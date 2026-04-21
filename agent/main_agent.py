import asyncio
import os
import re
from pathlib import Path
from typing import List, Dict

from dotenv import load_dotenv
from openai import AsyncOpenAI

from data.legal_chunker import load_legal_chunks


VN_STOPWORDS = {
    "và", "là", "của", "cho", "các", "một", "được", "theo", "điều", "khoản", "này",
    "trong", "với", "khi", "về", "như", "để", "đối", "với", "có", "tại", "hay",
}


def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"\w+", text.lower(), flags=re.UNICODE)
    return [token for token in tokens if token not in VN_STOPWORDS and len(token) > 1]

class MainAgent:
    """
    Đây là Agent mẫu sử dụng kiến trúc RAG đơn giản.
    Sinh viên nên thay thế phần này bằng Agent thực tế đã phát triển ở các buổi trước.
    """
    def __init__(self, retrieval_mode: str = "optimized"):
        self.retrieval_mode = retrieval_mode
        self.name = f"SupportAgent-{retrieval_mode}"
        root_dir = Path(__file__).resolve().parents[1]
        load_dotenv(root_dir / ".env")
        api_key = (
            os.getenv("OPENAI_API_KEY")
            or os.getenv("OPENAIKEY")
            or os.getenv("OpenAIKEY")
        )
        if not api_key:
            raise ValueError(
                "Không tìm thấy OpenAI key. Hãy set OPENAI_API_KEY (hoặc OpenAIKEY) trong .env"
            )
        self.answer_model = os.getenv("ANSWER_MODEL", "gpt-4o-mini")
        self.client = AsyncOpenAI(api_key=api_key)

        data_path = Path(__file__).resolve().parents[1] / "data" / "data_legal.txt"
        self.chunks = load_legal_chunks(str(data_path))
        self.chunk_tokens = [set(_tokenize(chunk["text"])) for chunk in self.chunks]

    def _retrieve(self, question: str, top_k: int = 3) -> List[Dict]:
        query_tokens = set(_tokenize(question))
        if self.retrieval_mode == "baseline":
            query_tokens = {token for token in query_tokens if not token.isdigit()}
        article_match = re.search(r"điều\s+(\d+)", question, flags=re.IGNORECASE)
        clause_match = re.search(r"khoản\s+(\d+)", question, flags=re.IGNORECASE)

        target_article = article_match.group(1) if article_match else None
        target_clause = clause_match.group(1) if clause_match else None

        scored = []

        for chunk, tokens in zip(self.chunks, self.chunk_tokens):
            score = len(query_tokens.intersection(tokens))
            metadata = chunk.get("metadata", {})

            if self.retrieval_mode == "optimized":
                if target_article and metadata.get("article") == target_article:
                    score += 20
                if target_clause and metadata.get("clause") == target_clause:
                    score += 8

            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)

        if not scored:
            return self.chunks[:top_k]
        return [chunk for _, chunk in scored[:top_k]]

    async def query(self, question: str) -> Dict:
        """
        Mô phỏng quy trình RAG:
        1. Retrieval: Tìm kiếm context liên quan.
        2. Generation: Gọi LLM để sinh câu trả lời.
        """
        top_k = 1 if self.retrieval_mode == "baseline" else 3
        retrieved_chunks = self._retrieve(question, top_k=top_k)
        retrieved_ids: List[str] = []
        for chunk in retrieved_chunks:
            retrieved_ids.append(chunk["id"])
            if self.retrieval_mode == "optimized":
                parent_id = chunk.get("metadata", {}).get("parent_article_id")
                if parent_id:
                    retrieved_ids.append(parent_id)

        # Giữ thứ tự và loại trùng
        seen = set()
        retrieved_ids = [doc_id for doc_id in retrieved_ids if not (doc_id in seen or seen.add(doc_id))]
        contexts = [chunk["text"] for chunk in retrieved_chunks]

        context_block = "\n\n".join(
            [f"[Context {idx+1}] {context}" for idx, context in enumerate(contexts)]
        )

        response = await self.client.chat.completions.create(
            model=self.answer_model,
            temperature=0.1,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Bạn là trợ lý pháp lý. Chỉ trả lời dựa trên context được cung cấp. "
                        "Nếu context không đủ, hãy nói rõ không đủ thông tin."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Câu hỏi: {question}\n\n"
                        f"Context:\n{context_block}\n\n"
                        "Trả lời ngắn gọn, chính xác, nêu đúng Điều/khoản nếu có."
                    ),
                },
            ],
        )

        answer_text = (response.choices[0].message.content or "").strip()
        usage_total = response.usage.total_tokens if response.usage else 0

        return {
            "answer": answer_text,
            "contexts": contexts,
            "metadata": {
                "model": self.answer_model,
                "tokens_used": usage_total,
                "sources": ["data/data_legal.txt"],
                "retrieval_mode": self.retrieval_mode,
                "retrieved_ids": retrieved_ids,
            }
        }

if __name__ == "__main__":
    agent = MainAgent()
    async def test():
        resp = await agent.query("Làm thế nào để đổi mật khẩu?")
        print(resp)
    asyncio.run(test())
