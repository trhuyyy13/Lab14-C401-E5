import json
import asyncio
import sys
import os
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from data.legal_chunker import load_legal_chunks

def _resolve_openai_key() -> str:
    load_dotenv(ROOT_DIR / ".env")
    key = (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("OPENAIKEY")
        or os.getenv("OpenAIKEY")
    )
    if not key:
        raise ValueError(
            "Không tìm thấy OpenAI key. Hãy set OPENAI_API_KEY (hoặc OpenAIKEY) trong .env"
        )
    os.environ["OPENAI_API_KEY"] = key
    return key


def _build_prompt(chunk: Dict[str, Any], variant: str) -> str:
    metadata = chunk["metadata"]
    article = metadata.get("article")
    clause = metadata.get("clause")

    task_hint = {
        "fact": "Tạo 1 câu hỏi fact-check ngắn, rõ ràng.",
        "clause": "Tạo 1 câu hỏi tập trung vào chi tiết khoản/điểm.",
        "scope": "Tạo 1 câu hỏi hỏi về phạm vi/ý nghĩa điều luật.",
        "adversarial": "Tạo 1 câu hỏi gây nhiễu nhẹ nhưng vẫn trả lời được từ context.",
    }.get(variant, "Tạo 1 câu hỏi fact-check.")

    return (
        "Bạn là chuyên gia tạo dataset đánh giá RAG pháp lý tiếng Việt.\n"
        "Sinh DUY NHẤT JSON object hợp lệ với các key: question, expected_answer, difficulty, type.\n"
        "Ràng buộc:\n"
        "- question: tiếng Việt, 1 câu, cụ thể theo context.\n"
        "- expected_answer: ngắn gọn 1-3 câu, chỉ dựa trên context.\n"
        "- difficulty: one of easy|medium|hard.\n"
        "- type: one of fact-check|scope|adversarial|ambiguous.\n"
        f"- Ưu tiên bám Điều {article}"
        f"{', khoản ' + clause if clause else ''}.\n"
        f"Yêu cầu biến thể: {task_hint}\n\n"
        "CONTEXT:\n"
        f"{chunk['text']}"
    )


async def _generate_case_with_llm(
    client: AsyncOpenAI,
    chunk: Dict[str, Any],
    variant: str,
    sem: asyncio.Semaphore,
) -> Dict[str, Any]:
    metadata = chunk["metadata"]
    prompt = _build_prompt(chunk, variant)

    async with sem:
        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Bạn tạo dữ liệu benchmark chính xác, không bịa ngoài context."},
                {"role": "user", "content": prompt},
            ],
        )

    content = completion.choices[0].message.content or "{}"
    parsed = json.loads(content)

    question = str(parsed.get("question", "")).strip()
    expected_answer = str(parsed.get("expected_answer", "")).strip() or chunk["text"][:280]
    difficulty = str(parsed.get("difficulty", "medium")).strip().lower()
    case_type = str(parsed.get("type", "fact-check")).strip().lower()

    if not question:
        article = metadata.get("article", "?")
        question = f"Theo Điều {article}, nội dung chính được quy định như thế nào?"

    if difficulty not in {"easy", "medium", "hard"}:
        difficulty = "medium"

    if case_type not in {"fact-check", "scope", "adversarial", "ambiguous"}:
        case_type = "fact-check"

    return {
        "question": question,
        "expected_answer": expected_answer,
        "context": chunk["text"],
        "expected_retrieval_ids": [chunk["id"], metadata["parent_article_id"]],
        "metadata": {
            "difficulty": difficulty,
            "type": case_type,
            "chunk_id": chunk["id"],
            "article": metadata.get("article"),
            "chapter": metadata.get("chapter"),
            "model": "gpt-4o-mini",
        },
    }


async def generate_qa_from_legal_chunks(num_pairs: int = 60) -> List[Dict]:
    _resolve_openai_key()
    client = AsyncOpenAI()
    chunks = load_legal_chunks("data/data_legal.txt")
    print(f"Loaded {len(chunks)} legal chunks from data_legal.txt")

    if not chunks:
        return []

    selected_chunks = chunks[:num_pairs] if len(chunks) >= num_pairs else chunks
    variants = ["fact", "clause", "scope", "adversarial"]
    sem = asyncio.Semaphore(6)

    tasks = []
    for idx, chunk in enumerate(selected_chunks):
        variant = variants[idx % len(variants)]
        tasks.append(_generate_case_with_llm(client, chunk, variant, sem))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    cases: List[Dict] = []
    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            fallback_chunk = selected_chunks[idx]
            fallback_metadata = fallback_chunk["metadata"]
            cases.append(
                {
                    "question": f"Theo Điều {fallback_metadata.get('article')}, quy định chính là gì?",
                    "expected_answer": fallback_chunk["text"][:280],
                    "context": fallback_chunk["text"],
                    "expected_retrieval_ids": [
                        fallback_chunk["id"],
                        fallback_metadata["parent_article_id"],
                    ],
                    "metadata": {
                        "difficulty": "medium",
                        "type": "fact-check",
                        "chunk_id": fallback_chunk["id"],
                        "article": fallback_metadata.get("article"),
                        "chapter": fallback_metadata.get("chapter"),
                        "model": "fallback",
                    },
                }
            )
        else:
            cases.append(result)

    if len(cases) < num_pairs and chunks:
        idx = 0
        while len(cases) < num_pairs:
            base_chunk = chunks[idx % len(chunks)]
            metadata = base_chunk["metadata"]
            cases.append(
                {
                    "question": f"Điều {metadata.get('article')} quy định nội dung gì?",
                    "expected_answer": base_chunk["text"][:280],
                    "context": base_chunk["text"],
                    "expected_retrieval_ids": [base_chunk["id"], metadata["parent_article_id"]],
                    "metadata": {
                        "difficulty": "easy",
                        "type": "fact-check",
                        "chunk_id": base_chunk["id"],
                        "article": metadata.get("article"),
                        "chapter": metadata.get("chapter"),
                        "model": "fallback",
                    },
                }
            )
            idx += 1

    return cases[:num_pairs]

async def main():
    qa_pairs = await generate_qa_from_legal_chunks(num_pairs=60)
    
    with open("data/golden_set.jsonl", "w", encoding="utf-8") as f:
        for pair in qa_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")
    print(f"Done! Saved {len(qa_pairs)} cases to data/golden_set.jsonl")

if __name__ == "__main__":
    asyncio.run(main())
