import asyncio
import os
from typing import Dict

from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

SYSTEM_PROMPT = """Bạn là trợ lý pháp lý chuyên về luật và nghị định Việt Nam.
Hãy trả lời câu hỏi của người dùng DỰA TRÊN ngữ cảnh (context) được cung cấp.
- Nếu câu trả lời có trong context, hãy trả lời chính xác, ngắn gọn và chuyên nghiệp.
- Nếu thông tin KHÔNG có trong context, hãy nói rõ: "Tôi không tìm thấy thông tin này trong tài liệu."
- Không được bịa đặt hoặc suy diễn thông tin ngoài context."""


class MainAgent:
    """
    RAG Agent thực tế:
    - Retrieval: ChromaDB + OpenAI text-embedding-3-small
    - Generation: GPT-4o-mini
    - Nguồn dữ liệu: Luật Cán bộ Công chức & Nghị định BHYT
    """

    def __init__(self, version: str = "v1"):
        self.name = f"LegalRAGAgent-{version}"
        self.version = version
        self._openai = AsyncOpenAI(api_key=OPENAI_API_KEY)
        # V2: dùng system prompt chặt chẽ hơn + top_k cao hơn
        self._top_k = 5 if version == "v2" else 3
        self._temperature = 0.0 if version == "v2" else 0.1

        # Khởi tạo ChromaDB ngay tại main thread để tránh lỗi tenant trong worker threads
        import chromadb
        from chromadb.utils import embedding_functions

        db_client = chromadb.PersistentClient(path="data/chroma_db")
        openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=OPENAI_API_KEY,
            model_name="text-embedding-3-small",
        )
        self._collection = db_client.get_or_create_collection(
            name="legal_docs",
            embedding_function=openai_ef,
            metadata={"hnsw:space": "cosine"},
        )
        if self._collection.count() == 0:
            raise RuntimeError(
                "ChromaDB collection trống. Hãy chạy 'python data/ingest.py' trước."
            )

    def _retrieve(self, question: str):
        """Synchronous retrieval — sẽ được gọi qua asyncio.to_thread."""
        results = self._collection.query(
            query_texts=[question],
            n_results=self._top_k,
            include=["documents", "metadatas", "distances"],
        )
        return results

    async def query(self, question: str) -> Dict:
        """
        Quy trình RAG:
        1. Embed câu hỏi & tìm top-k chunks gần nhất trong ChromaDB.
        2. Ghép context và gọi GPT-4o-mini để sinh câu trả lời.
        """
        # 1. Retrieval (chạy trong thread để không block event loop)
        results = await asyncio.to_thread(self._retrieve, question)

        contexts = results["documents"][0]
        retrieved_ids = results["ids"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        # 2. Xây dựng context string
        context_parts = []
        for doc, meta, dist in zip(contexts, metadatas, distances):
            source_label = (
                "Luật Cán bộ Công chức"
                if meta["source"] == "luat_can_bo_cong_chuc"
                else "Nghị định BHYT"
            )
            context_parts.append(
                f"[{source_label} - Điều {meta['article_num']} (score: {1 - dist:.2f})]:\n{doc}"
            )
        context_str = "\n\n---\n\n".join(context_parts)

        # 3. Generation
        user_message = f"Ngữ cảnh:\n{context_str}\n\nCâu hỏi: {question}"
        response = await self._openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=self._temperature,
            max_tokens=512,
        )

        answer = response.choices[0].message.content.strip()
        tokens_used = response.usage.total_tokens

        return {
            "answer": answer,
            "contexts": contexts,
            "retrieved_ids": retrieved_ids,
            "metadata": {
                "model": "gpt-4o-mini",
                "tokens_used": tokens_used,
                "sources": list({m["source"] for m in metadatas}),
                "agent_version": self.version,
            },
        }


if __name__ == "__main__":
    agent = MainAgent()

    async def test():
        resp = await agent.query("Công chức là gì?")
        print("Answer:", resp["answer"])
        print("Retrieved IDs:", resp["retrieved_ids"])

    asyncio.run(test())
