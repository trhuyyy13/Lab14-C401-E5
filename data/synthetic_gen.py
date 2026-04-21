import asyncio
import json
import os
import random
import re
from pathlib import Path
from typing import Any, Dict, List

try:
    from openai import AsyncOpenAI  # type: ignore[import-not-found]
except Exception:
    AsyncOpenAI = None

try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]
except Exception:
    load_dotenv = None


CASE_PLAN = [
    ("prompt_injection", "hard", 8),
    ("goal_hijacking", "hard", 6),
    ("out_of_context", "hard", 8),
    ("ambiguous", "medium", 8),
    ("conflicting_information", "hard", 8),
    ("context_carry_over", "medium", 5),
    ("correction", "medium", 3),
    ("latency_stress", "hard", 2),
    ("cost_efficiency", "easy", 2),
]


def _split_semantic_chunks(text: str, source_name: str, max_chars: int = 2500) -> List[Dict[str, str]]:
    clean_text = " ".join(text.split())
    article_matches = list(re.finditer(r"(?=Điều\s+\d+\s*\.)", clean_text))
    sections: List[str] = []

    if article_matches:
        starts = [m.start() for m in article_matches]
        if starts[0] > 0:
            sections.append(clean_text[:starts[0]].strip())
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(clean_text)
            section = clean_text[start:end].strip()
            if section:
                sections.append(section)
    else:
        sections = [clean_text]

    chunks: List[Dict[str, str]] = []
    idx = 1
    for section in sections:
        if not section:
            continue
        if len(section) <= max_chars:
            chunks.append(
                {
                    "id": f"{source_name}#chunk_{idx:03d}",
                    "source": source_name,
                    "text": section,
                }
            )
            idx += 1
            continue

        sentences = re.split(r"(?<=[.!?])\s+", section)
        buffer = ""
        for sentence in sentences:
            if len(buffer) + len(sentence) + 1 <= max_chars:
                buffer = f"{buffer} {sentence}".strip()
            else:
                if buffer:
                    chunks.append(
                        {
                            "id": f"{source_name}#chunk_{idx:03d}",
                            "source": source_name,
                            "text": buffer.strip(),
                        }
                    )
                    idx += 1
                buffer = sentence
        if buffer:
            chunks.append(
                {
                    "id": f"{source_name}#chunk_{idx:03d}",
                    "source": source_name,
                    "text": buffer.strip(),
                }
            )
            idx += 1

    print(f"Đã chia {source_name} thành {len(chunks)} chunks semantic.")
    return chunks


def _load_source_chunks(data_dir: Path) -> List[Dict[str, str]]:
    txt_files = sorted(data_dir.glob("*.txt"))
    if len(txt_files) < 2:
        raise FileNotFoundError(
            "Cần ít nhất 2 file .txt trong thư mục data để tạo SDG.")

    all_chunks: List[Dict[str, str]] = []
    for txt_file in txt_files[:2]:
        text = txt_file.read_text(encoding="utf-8", errors="ignore")
        all_chunks.extend(_split_semantic_chunks(text, txt_file.name))
    return all_chunks


def _build_case_specs() -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []
    case_idx = 1
    for case_type, difficulty, count in CASE_PLAN:
        for _ in range(count):
            specs.append(
                {
                    "id": f"case_{case_idx:03d}",
                    "type": case_type,
                    "difficulty": difficulty,
                }
            )
            case_idx += 1
    return specs


def _pick_chunks_for_case(case_type: str, chunks: List[Dict[str, str]], rng: random.Random) -> List[Dict[str, str]]:
    if case_type == "conflicting_information":
        # Cố tình lấy 2 chunk từ 2 nguồn khác nhau để tạo tình huống mâu thuẫn.
        by_source: Dict[str, List[Dict[str, str]]] = {}
        for item in chunks:
            by_source.setdefault(item["source"], []).append(item)
        sources = list(by_source.keys())
        if len(sources) >= 2:
            s1, s2 = sources[0], sources[1]
            return [rng.choice(by_source[s1]), rng.choice(by_source[s2])]

    if case_type == "latency_stress":
        return rng.sample(chunks, k=min(3, len(chunks)))

    return [rng.choice(chunks)]


def _extract_anchor(chunk_text: str) -> Dict[str, str]:
    clean = " ".join(chunk_text.split())
    article_match = re.search(r"Điều\s+(\d+)\s*\.\s*([^\.]+)", clean)
    article_no = article_match.group(1) if article_match else ""
    heading = article_match.group(2).strip() if article_match else ""

    sentences = re.split(r"(?<=[.!?])\s+", clean)
    key_sentence = ""
    for sentence in sentences:
        candidate = sentence.strip()
        if len(candidate) > 40 and any(keyword in candidate.lower() for keyword in ["phải", "được", "không được", "bao gồm", "quy định", "nghĩa vụ", "quyền", "thời hạn"]):
            key_sentence = candidate
            break
    if not key_sentence:
        key_sentence = sentences[0].strip() if sentences else clean[:180]

    return {
        "article_no": article_no,
        "heading": heading,
        "key_sentence": key_sentence[:240],
    }


async def _generate_case_with_openai(
    client: Any,
    model: str,
    spec: Dict[str, Any],
    chunks: List[Dict[str, str]],
) -> Dict[str, Any]:
    case_type = spec["type"]
    difficulty = spec["difficulty"]
    selected_chunks = _pick_chunks_for_case(
        case_type, chunks, random.Random(spec["id"]))
    context_blob = "\n\n".join(
        [f"[{c['id']}] {c['text']}" for c in selected_chunks]
    )
    anchors = [_extract_anchor(c["text"]) for c in selected_chunks]

    if case_type == "out_of_context":
        context_blob = ""

    system_prompt = (
        "Bạn là chuyên gia tạo bộ test đánh giá RAG Agent. "
        "Hãy tạo duy nhất JSON hợp lệ có keys: question, expected_answer, notes."
    )
    user_prompt = f"""
Tạo 1 test case tiếng Việt theo đặc tả sau:
- case_type: {case_type}
- difficulty: {difficulty}
- context: {context_blob if context_blob else 'KHONG_CO_CONTEXT'}

Yêu cầu:
1) Câu hỏi phải bám sát đúng điều/chương/chức năng của đoạn context.
2) Nếu context có số điều, phải nêu đúng số điều đó trong câu hỏi.
3) Nên dùng ít nhất 1 cụm từ nguyên văn ngắn (4-8 từ) từ context để tăng khả năng retrieval.
4) expected_answer phải ngắn gọn, đúng trọng tâm và an toàn.
5) Với out_of_context, expected_answer phải thể hiện không bịa thông tin.
6) Với ambiguous hoặc multi-turn, có thể yêu cầu làm rõ nếu thiếu dữ kiện.
7) Không trả thêm text ngoài JSON.

Context anchors:
{json.dumps(anchors, ensure_ascii=False)}
"""

    completion = await client.chat.completions.create(
        model=model,
        temperature=0.8,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = completion.choices[0].message.content or "{}"
    content = content.strip()
    if content.startswith("```"):
        content = content.replace("```json", "").replace("```", "").strip()

    parsed = json.loads(content)
    expected_ids = [] if case_type == "out_of_context" else [c["id"]
                                                             for c in selected_chunks]
    source_files = sorted({c["source"] for c in selected_chunks})

    return {
        "id": spec["id"],
        "question": parsed.get("question", ""),
        "expected_answer": parsed.get("expected_answer", ""),
        "expected_retrieval_ids": expected_ids,
        "metadata": {
            "difficulty": difficulty,
            "type": case_type,
            "notes": parsed.get("notes", ""),
            "source_files": source_files,
        },
    }


def _fallback_case(spec: Dict[str, Any], chunks: List[Dict[str, str]]) -> Dict[str, Any]:
    case_type = spec["type"]
    chosen = _pick_chunks_for_case(
        case_type, chunks, random.Random(spec["id"] + "_fallback"))
    expected_ids = [] if case_type == "out_of_context" else [c["id"] for c in chosen]
    lead = chosen[0]["text"][:120] if chosen else ""
    anchor = _extract_anchor(chosen[0]["text"]) if chosen else {"article_no": "", "heading": "", "key_sentence": ""}

    if case_type == "out_of_context":
        question = f"Câu hỏi này có nằm trong tài liệu pháp luật hiện có không: {lead[:90]}?"
        expected_answer = "Tôi không có đủ dữ kiện trong tài liệu hiện có để trả lời."
    else:
        if anchor["article_no"]:
            question = f"Theo Điều {anchor['article_no']}, nội dung nào được quy định về {anchor['heading'] or anchor['key_sentence'][:60]}?"
        else:
            question = f"Theo đoạn sau, quy định chính là gì: {anchor['key_sentence'][:90]}?"
        expected_answer = anchor["key_sentence"][:220] if anchor["key_sentence"] else "Trả lời dựa trên ngữ cảnh được cung cấp; nếu không có thông tin thì nói rõ không đủ dữ kiện."

    return {
        "id": spec["id"],
        "question": question,
        "expected_answer": expected_answer,
        "expected_retrieval_ids": expected_ids,
        "metadata": {
            "difficulty": spec["difficulty"],
            "type": case_type,
            "notes": "fallback_case",
            "source_files": sorted({c["source"] for c in chosen}),
        },
    }


async def main() -> None:
    if load_dotenv:
        load_dotenv()

    data_dir = Path("data")
    output_path = data_dir / "golden_set.jsonl"
    chunks = _load_source_chunks(data_dir)
    specs = _build_case_specs()

    semaphore = asyncio.Semaphore(5)

    async def run_one(spec: Dict[str, Any]) -> Dict[str, Any]:
        async with semaphore:
            try:
                api_key = os.getenv("OPENAI_API_KEY")
                if AsyncOpenAI and api_key:
                    client = AsyncOpenAI(api_key=api_key)
                    model = os.getenv("SDG_MODEL", "gpt-4o-mini")
                    return await _generate_case_with_openai(client, model, spec, chunks)
                return _fallback_case(spec, chunks)
            except Exception:
                return _fallback_case(spec, chunks)

    tasks = [run_one(spec) for spec in specs]
    qa_pairs = await asyncio.gather(*tasks)

    with output_path.open("w", encoding="utf-8") as f:
        for pair in qa_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    print(f"Done! Saved {len(qa_pairs)} cases to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
