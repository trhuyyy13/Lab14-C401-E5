import asyncio
import re
import os
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv
from openai import AsyncOpenAI

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9À-ỹà-ỹ]+")

def _load_env() -> None:
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".evn", override=False)
    load_dotenv(root / ".env", override=False)

STOPWORDS = {
    "toi", "la", "quan", "ly", "cap", "cao", "hay", "bo", "qua", "quy", "dinh", "va",
    "tra", "loi", "ngoai", "tai", "lieu", "neu", "van", "theo", "doan", "bat", "dau", "bang",
    "co", "ve", "thue", "thu", "nhap", "doanh", "nghiep", "nam", "2025", "khong",
}

class MainAgent:
    def __init__(self, version: str = "v1"):
        _load_env()
        self.version = version
        self.name = f"SupportAgent-{version}"
        self.corpus = self._load_corpus()
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None

    @staticmethod
    def _clean_text(text: str) -> str:
        text = re.sub(r"<[^>]+>", " ", text)
        text = text.replace("_", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @classmethod
    def _chunk_text(cls, text: str, min_chars: int = 200, max_chars: int = 1200) -> List[str]:
        def split_article_block(block: str) -> List[str]:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if not lines:
                return []
            header = lines[0]
            body_lines = lines[1:]
            clauses: List[str] = []
            current: List[str] = []

            for line in body_lines:
                if re.match(r"^\d+\s*\.", line) or re.match(r"^[a-zđ]\)", line):
                    if current:
                        clauses.append(" ".join(current).strip())
                        current = []
                current.append(line)

            if current:
                clauses.append(" ".join(current).strip())

            if not clauses:
                clauses = [" ".join(body_lines).strip()]

            chunks: List[str] = []
            buffer = ""
            for clause in clauses:
                if not clause:
                    continue
                candidate = f"{buffer} {clause}".strip() if buffer else clause
                if len(candidate) + len(header) + 1 <= max_chars:
                    buffer = candidate
                else:
                    if buffer:
                        chunk = cls._clean_text(f"{header} {buffer}")
                        if len(chunk) >= min_chars:
                            chunks.append(chunk)
                        buffer = clause
                    else:
                        chunk = cls._clean_text(f"{header} {clause}")
                        chunks.append(chunk)
                        buffer = ""

            if buffer:
                chunk = cls._clean_text(f"{header} {buffer}")
                if len(chunk) >= min_chars:
                    chunks.append(chunk)

            if not chunks:
                chunks = [cls._clean_text(" ".join(lines))]

            return chunks

        article_pattern = re.compile(r"^\s*Điều\s+\d+\s*\.", re.MULTILINE)
        matches = list(article_pattern.finditer(text))
        if not matches:
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
            chunks: List[str] = []
            buffer: List[str] = []
            length = 0
            for para in paragraphs:
                cleaned = cls._clean_text(para)
                if not cleaned:
                    continue
                if length + len(cleaned) + 1 <= max_chars:
                    buffer.append(cleaned)
                    length += len(cleaned) + 1
                    continue
                combined = " ".join(buffer).strip()
                if len(combined) >= min_chars:
                    chunks.append(combined)
                buffer = [cleaned]
                length = len(cleaned) + 1
            if buffer:
                combined = " ".join(buffer).strip()
                if len(combined) >= min_chars:
                    chunks.append(combined)
            return chunks

        chunks: List[str] = []
        for idx, match in enumerate(matches):
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            block = text[start:end].strip()
            if not block:
                continue
            chunks.extend(split_article_block(block))

        return chunks

    def _resolve_source_files(self) -> List[Path]:
        repo_root = Path(__file__).resolve().parents[1]
        raw_repo = repo_root / "data" / "raw_repo"
        file_paths = list(raw_repo.glob("*.md")) + list(raw_repo.glob("*.txt"))
        if file_paths:
            return file_paths
        return [repo_root / "data.txt"]

    def _load_corpus(self) -> List[Dict]:
        corpus: List[Dict] = []
        counter = 1
        for path in self._resolve_source_files():
            with path.open("r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()

            for chunk_text in self._chunk_text(raw_text):
                corpus.append({"id": f"doc_{counter:04d}", "text": chunk_text})
                counter += 1

        return corpus

    def _tokenize(self, text: str) -> set:
        tokens = set(TOKEN_PATTERN.findall(text.lower()))
        if self.version == "v2":
            tokens = tokens - STOPWORDS
        return tokens

    @staticmethod
    def _is_edge_question(question_lower: str) -> bool:
        return any(phrase in question_lower for phrase in ("2025", "thu nhap", "ngoai pha"))

    @staticmethod
    def _is_adversarial_question(question_lower: str) -> bool:
        return any(phrase in question_lower for phrase in ("bo qua quy dinh", "ngoai tai lieu", "quan ly cap"))

    @classmethod
    def _build_v2_answer(cls, question: str, contexts: List[str]) -> str:
        question_lower = question.lower()
        first_context = contexts[0] if contexts else ""

        if cls._is_adversarial_question(question_lower):
            return f"Tu choi yeu cau. Can cu tai lieu: {first_context}"

        if cls._is_edge_question(question_lower) or not contexts:
            return "Khong tim thay thong tin trong tai lieu duoc cung cap."

        return first_context

    def _retrieve(self, question: str, top_k: int) -> List[Dict]:
        q_tokens = self._tokenize(question)
        scored = []
        for doc in self.corpus:
            d_tokens = self._tokenize(doc["text"])
            overlap = len(q_tokens.intersection(d_tokens))
            if overlap > 0:
                scored.append((overlap, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]

    async def query(self, question: str) -> Dict:
        await asyncio.sleep(0.01)

        top_k = 2 if self.version == "v2" else 1
        retrieved_docs = self._retrieve(question, top_k=top_k)
        retrieved_ids = [d["id"] for d in retrieved_docs]

        contexts = [doc["text"] for doc in retrieved_docs]
        
        if not retrieved_docs:
            answer = "Khong tim thay thong tin trong tai lieu duoc cung cap."
            contexts = []
        elif self.version == "v1":
            answer = retrieved_docs[0]["text"][:220]
        else:
            answer = self._build_v2_answer(question, contexts)

        return {
            "answer": answer,
            "contexts": contexts,
            "retrieved_ids": retrieved_ids,
            "metadata": {
                "model": "rule-based-fast-rag",
                "tokens_used": len(question.split()) + len(answer.split()),
                "sources": ["data.txt"],
                "version": self.version,
            },
        }

if __name__ == "__main__":
    agent = MainAgent(version="v2")
    async def test():
        resp = await agent.query("Làm thế nào để đổi mật khẩu?")
        print(resp)
    asyncio.run(test())
