import asyncio
import math
import os
import re
import unicodedata
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from openai import OpenAI  # type: ignore[import-not-found]
except Exception:
    OpenAI = None


VIETNAMESE_STOPWORDS = {
    "và", "là", "của", "các", "một", "những", "được", "theo", "cho", "với",
    "trong", "tại", "có", "không", "khi", "để", "về", "do", "này", "đó",
    "thì", "lại", "nên", "phải", "bị", "rằng", "như", "hay", "hoặc", "từ",
    "đến", "ra", "đi", "đã", "sẽ", "đang", "cùng", "vì", "nếu", "thì",
}


class MainAgent:
    """Agent RAG nội bộ dùng hybrid retrieval: embedding > rerank > TF-IDF cải tiến."""

    def __init__(self, data_dir: str = "data", top_k: int = 3, candidate_k: int = 12):
        self.name = "SupportAgent-v4-hybrid-retrieval"
        self.data_dir = Path(data_dir)
        self.top_k = top_k
        self.candidate_k = candidate_k
        self.chunk_size = 2500
        self.overlap = 180

        self.embedding_model = os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        api_key = os.getenv("OPENAI_API_KEY")
        self.retrieval_mode = os.getenv(
            "RETRIEVAL_MODE",
            "embedding" if api_key and OpenAI else "hybrid",
        ).lower()
        self.embedding_client = OpenAI(api_key=api_key) if (
            OpenAI and api_key) else None

        self.chunks: List[Dict] = []
        self.idf: Dict[str, float] = {}
        self.char_idf: Dict[str, float] = {}
        self.avgdl: float = 1.0
        self.chunk_embeddings: List[List[float]] = []
        self._embedding_ready: bool = False
        self._build_index()

    @staticmethod
    def _strip_accents(text: str) -> str:
        normalized = unicodedata.normalize("NFD", text or "")
        without_marks = "".join(
            ch for ch in normalized if unicodedata.category(ch) != "Mn")
        return unicodedata.normalize("NFC", without_marks)

    @classmethod
    def _normalize_text(cls, text: str) -> str:
        text = cls._strip_accents((text or "").lower())
        text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @classmethod
    def _tokenize(cls, text: str) -> List[str]:
        tokens = re.findall(
            r"\w+", cls._normalize_text(text), flags=re.UNICODE)
        return [token for token in tokens if token not in VIETNAMESE_STOPWORDS and len(token) > 1]

    @staticmethod
    def _char_ngrams(text: str, n: int = 3) -> List[str]:
        normalized = re.sub(r"\s+", " ", MainAgent._normalize_text(text))
        padded = f"  {normalized}  "
        if len(padded) < n:
            return [padded]
        return [padded[i:i + n] for i in range(len(padded) - n + 1)]

    def _chunk_text(self, text: str, source_name: str) -> List[Dict]:
        clean_text = " ".join((text or "").split())
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

        chunks: List[Dict] = []
        idx = 1
        for section in sections:
            if not section:
                continue
            if len(section) <= self.chunk_size:
                chunks.append(
                    {
                        "chunk_index": idx - 1,
                        "id": f"{source_name}#chunk_{idx:03d}",
                        "source": source_name,
                        "text": section,
                        "tokens": self._tokenize(section),
                        "normalized_text": self._normalize_text(section),
                        "char_ngrams": self._char_ngrams(section),
                    }
                )
                idx += 1
                continue

            sentences = re.split(r"(?<=[.!?])\s+", section)
            buffer = ""
            for sentence in sentences:
                candidate = f"{buffer} {sentence}".strip(
                ) if buffer else sentence
                if len(candidate) <= self.chunk_size:
                    buffer = candidate
                else:
                    if buffer:
                        chunks.append(
                            {
                                "chunk_index": idx - 1,
                                "id": f"{source_name}#chunk_{idx:03d}",
                                "source": source_name,
                                "text": buffer.strip(),
                                "tokens": self._tokenize(buffer),
                                "normalized_text": self._normalize_text(buffer),
                                "char_ngrams": self._char_ngrams(buffer),
                            }
                        )
                        idx += 1
                    buffer = sentence
            if buffer:
                chunks.append(
                    {
                        "chunk_index": idx - 1,
                        "id": f"{source_name}#chunk_{idx:03d}",
                        "source": source_name,
                        "text": buffer.strip(),
                        "tokens": self._tokenize(buffer),
                        "normalized_text": self._normalize_text(buffer),
                        "char_ngrams": self._char_ngrams(buffer),
                    }
                )
                idx += 1
        return chunks

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not self.embedding_client or not texts:
            return []

        embeddings: List[List[float]] = []
        batch_size = 64
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            response = self.embedding_client.embeddings.create(
                model=self.embedding_model,
                input=batch,
            )
            embeddings.extend([item.embedding for item in response.data])
        return embeddings

    def _ensure_query_embedding(self, question: str) -> Optional[List[float]]:
        if not self.embedding_client:
            return None
        query_embedding_vecs = self._embed_texts([question])
        return query_embedding_vecs[0] if query_embedding_vecs else None

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _build_index(self) -> None:
        txt_files = sorted(self.data_dir.glob("*.txt"))
        all_chunks: List[Dict] = []
        for txt_file in txt_files:
            text = txt_file.read_text(encoding="utf-8", errors="ignore")
            all_chunks.extend(self._chunk_text(text, txt_file.name))

        self.chunks = all_chunks
        if not self.chunks:
            self.idf = {}
            self.avgdl = 1.0
            self.chunk_embeddings = []
            return

        doc_freq: Dict[str, int] = {}
        total_docs = len(self.chunks)
        total_len = 0
        for chunk in self.chunks:
            tokens = chunk["tokens"]
            total_len += len(tokens)
            for token in set(tokens):
                doc_freq[token] = doc_freq.get(token, 0) + 1

        self.avgdl = max(1.0, total_len / total_docs)
        self.idf = {
            token: math.log(1 + (total_docs - freq + 0.5) / (freq + 0.5))
            for token, freq in doc_freq.items()
        }

        char_doc_freq: Dict[str, int] = {}
        total_char_docs = len(self.chunks)
        for chunk in self.chunks:
            for gram in set(chunk.get("char_ngrams", [])):
                char_doc_freq[gram] = char_doc_freq.get(gram, 0) + 1

        self.char_idf = {
            gram: math.log(1 + (total_char_docs - freq + 0.5) / (freq + 0.5))
            for gram, freq in char_doc_freq.items()
        }

        if self.retrieval_mode in {"embedding", "hybrid"} and self.embedding_client:
            self.chunk_embeddings = self._embed_texts(
                [chunk["text"] for chunk in self.chunks])
            self._embedding_ready = len(self.chunk_embeddings) == len(self.chunks)
        else:
            self.chunk_embeddings = []
            self._embedding_ready = False

    def _bm25_score(self, query_tokens: List[str], chunk: Dict) -> float:
        if not query_tokens:
            return 0.0

        tokens = chunk.get("tokens", [])
        if not tokens:
            return 0.0

        tf = Counter(tokens)
        score = 0.0
        k1 = 1.6
        b = 0.75
        dl = len(tokens)
        for token, qtf in Counter(query_tokens).items():
            if token not in tf:
                continue
            idf = self.idf.get(token, 0.0)
            numerator = tf[token] * (k1 + 1)
            denominator = tf[token] + k1 * (1 - b + b * (dl / self.avgdl))
            score += idf * (numerator / denominator) * \
                (1.0 + 0.2 * min(qtf, 2))
        return score

    def _coverage_score(self, query_tokens: List[str], chunk: Dict) -> float:
        if not query_tokens:
            return 0.0
        chunk_tokens = set(chunk.get("tokens", []))
        if not chunk_tokens:
            return 0.0
        return len(set(query_tokens).intersection(chunk_tokens)) / max(1, len(set(query_tokens)))

    def _char_ngram_score(self, question: str, chunk: Dict) -> float:
        query_grams = self._char_ngrams(question)
        chunk_grams = Counter(chunk.get("char_ngrams", []))
        if not query_grams or not chunk_grams:
            return 0.0

        score = 0.0
        for gram in query_grams:
            if gram in chunk_grams:
                score += self.char_idf.get(gram, 0.0) * \
                    (chunk_grams[gram] / max(1, len(chunk_grams)))
        return score

    def _phrase_boost(self, question: str, chunk: Dict) -> float:
        q_norm = self._normalize_text(question)
        c_norm = chunk.get("normalized_text", "")
        if not q_norm or not c_norm:
            return 0.0
        query_tokens = self._tokenize(question)
        if len(query_tokens) >= 2:
            bigram = " ".join(query_tokens[:2])
            if bigram and bigram in c_norm:
                return 0.2
        if any(token in c_norm[:240] for token in query_tokens[:3]):
            return 0.08
        return 0.0

    def _article_boost(self, question: str, chunk: Dict) -> float:
        q_norm = self._normalize_text(question)
        c_norm = chunk.get("normalized_text", "")
        question_articles = re.findall(r"(?:dieu|đieu)\s*(\d+)", q_norm)
        if not question_articles:
            return 0.0
        for article_no in question_articles:
            if f"dieu {article_no}" in c_norm or f"đieu {article_no}" in c_norm:
                return 0.6
        return 0.0

    def _preamble_penalty(self, question: str, chunk: Dict) -> float:
        chunk_text = chunk.get("normalized_text", "")
        question_tokens = self._tokenize(question)
        if not chunk_text:
            return 0.0
        if chunk.get("chunk_index", 0) != 0:
            return 0.0
        if any(token in {"can", "cu", "luc", "hieu", "luc", "ban", "hanh"} for token in question_tokens):
            return 0.0
        if len(question_tokens) >= 4:
            return -0.12
        return 0.0

    def _rank_candidates(self, question: str) -> List[Tuple[float, Dict]]:
        query_tokens = self._tokenize(question)
        query_embedding: Optional[List[float]] = self._ensure_query_embedding(question) if self._embedding_ready else None

        lexical_ranked = []
        for chunk in self.chunks:
            bm25 = self._bm25_score(query_tokens, chunk)
            if bm25 > 0:
                lexical_ranked.append((bm25, chunk))
        lexical_ranked.sort(key=lambda item: item[0], reverse=True)

        if self.retrieval_mode in {"embedding", "hybrid"} and self._embedding_ready and query_embedding is not None:
            if query_embedding:
                similarities = []
                for chunk, embedding in zip(self.chunks, self.chunk_embeddings):
                    similarities.append((self._cosine_similarity(query_embedding, embedding), chunk))
                similarities.sort(key=lambda item: item[0], reverse=True)
                base_candidates = similarities[: self.candidate_k]
            else:
                base_candidates = lexical_ranked[: self.candidate_k]
        else:
            base_candidates = lexical_ranked[: self.candidate_k]

        reranked: List[Tuple[float, Dict]] = []
        for base_score, chunk in base_candidates:
            lexical = self._bm25_score(query_tokens, chunk)
            coverage = self._coverage_score(query_tokens, chunk)
            char_score = self._char_ngram_score(question, chunk)
            boost = self._phrase_boost(question, chunk)
            article_boost = self._article_boost(question, chunk)
            preamble_penalty = self._preamble_penalty(question, chunk)
            if self.retrieval_mode == "embedding" and self._embedding_ready:
                emb_score = 0.0
                if query_embedding is not None:
                    idx = chunk.get("chunk_index", -1)
                    if 0 <= idx < len(self.chunk_embeddings):
                        emb_score = self._cosine_similarity(
                            query_embedding, self.chunk_embeddings[idx])
                combined = 0.58 * emb_score + 0.14 * coverage + 0.12 * \
                    char_score + 0.08 * boost + article_boost + preamble_penalty
            elif self.retrieval_mode == "hybrid" and self._embedding_ready:
                emb_score = 0.0
                if query_embedding is not None:
                    idx = chunk.get("chunk_index", -1)
                    if 0 <= idx < len(self.chunk_embeddings):
                        emb_score = self._cosine_similarity(
                            query_embedding, self.chunk_embeddings[idx])
                combined = 0.35 * emb_score + 0.30 * lexical + 0.18 * char_score + \
                    0.08 * coverage + boost + article_boost + preamble_penalty
            else:
                combined = 0.42 * lexical + 0.24 * char_score + 0.16 * \
                    coverage + boost + article_boost + preamble_penalty
            reranked.append((combined, chunk))

        reranked.sort(key=lambda item: item[0], reverse=True)
        return reranked[: self.top_k]

    def _generate_answer(self, question: str, ranked_chunks: List[Tuple[float, Dict]]) -> str:
        if not ranked_chunks:
            return "Tôi không tìm thấy thông tin liên quan trong tài liệu hiện có để trả lời chính xác câu hỏi này."

        if ranked_chunks[0][0] < 0.08:
            return "Tôi không có đủ dữ kiện chắc chắn trong tài liệu để trả lời câu hỏi này."

        q_tokens = set(self._tokenize(question))
        snippets: List[Tuple[int, str]] = []
        for _, chunk in ranked_chunks:
            text = chunk["text"]
            sentences = re.split(r"(?<=[.!?])\s+", text)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                overlap = len(q_tokens.intersection(
                    set(self._tokenize(sentence))))
                if overlap > 0:
                    snippets.append((overlap, sentence))

        if not snippets:
            top_text = ranked_chunks[0][1]["text"]
            return top_text[:280].strip()

        snippets.sort(key=lambda x: x[0], reverse=True)
        selected: List[str] = []
        for _, sent in snippets:
            if sent not in selected:
                selected.append(sent)
            if len(selected) == 2:
                break
        return " ".join(selected)

    async def query(self, question: str, expected_retrieval_ids: Optional[List[str]] = None) -> Dict:
        """Trả lời câu hỏi bằng hybrid retrieval thật trên kho dữ liệu nội bộ."""
        await asyncio.sleep(0)
        _ = expected_retrieval_ids

        ranked_chunks = self._rank_candidates(question)
        retrieved_chunks = [chunk for _, chunk in ranked_chunks]
        retrieved_ids = [chunk["id"] for chunk in retrieved_chunks]
        answer = self._generate_answer(question, ranked_chunks)

        tokens_used = len(self._tokenize(
            question)) + sum(len(chunk.get("tokens", [])) for chunk in retrieved_chunks)

        return {
            "answer": answer,
            "contexts": [chunk["text"] for chunk in retrieved_chunks],
            "retrieved_ids": retrieved_ids,
            "metadata": {
                "model": f"local-rag-{self.retrieval_mode}",
                "retrieval_mode": self.retrieval_mode,
                "embedding_model": self.embedding_model if self.embedding_client else None,
                "tokens_used": tokens_used,
                "sources": sorted({chunk["source"] for chunk in retrieved_chunks}),
                "retrieved_ids": retrieved_ids,
            },
        }


if __name__ == "__main__":
    agent = MainAgent()

    async def test():
        resp = await agent.query("Điều kiện đăng ký dự tuyển công chức là gì?")
        print(resp)

    asyncio.run(test())
