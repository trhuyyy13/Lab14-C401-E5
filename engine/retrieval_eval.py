import re
from typing import Dict, List

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9À-ỹà-ỹ]+")

class RetrievalEvaluator:
    @staticmethod
    def _tokenize(text: str) -> set:
        return set(TOKEN_PATTERN.findall(text.lower()))

    @staticmethod
    def _safe_average(values: List[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    def calculate_hit_rate(self, expected_ids: List[str], retrieved_ids: List[str], top_k: int = 3) -> float:
        if not expected_ids:
            return 1.0 if not retrieved_ids else 0.0
        top_retrieved = retrieved_ids[:top_k]
        hit = any(doc_id in top_retrieved for doc_id in expected_ids)
        return 1.0 if hit else 0.0

    def calculate_mrr(self, expected_ids: List[str], retrieved_ids: List[str]) -> float:
        if not expected_ids:
            return 1.0 if not retrieved_ids else 0.0
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in expected_ids:
                return 1.0 / (i + 1)
        return 0.0

    async def score(self, test_case: Dict, response: Dict) -> Dict:
        expected_ids = test_case.get("expected_retrieval_ids", [])
        retrieved_ids = response.get("retrieved_ids", [])

        hit_rate = self.calculate_hit_rate(expected_ids, retrieved_ids, top_k=3)
        mrr = self.calculate_mrr(expected_ids, retrieved_ids)

        answer = response.get("answer", "")
        expected_answer = test_case.get("expected_answer", "")
        question = test_case.get("question", "")

        ans_tokens = self._tokenize(answer)
        gt_tokens = self._tokenize(expected_answer)
        q_tokens = self._tokenize(question)

        faithfulness = len(ans_tokens.intersection(gt_tokens)) / max(len(gt_tokens), 1)
        relevancy = len(ans_tokens.intersection(q_tokens)) / max(len(q_tokens), 1)

        return {
            "faithfulness": round(min(faithfulness, 1.0), 4),
            "relevancy": round(min(relevancy, 1.0), 4),
            "retrieval": {
                "hit_rate": hit_rate,
                "mrr": round(mrr, 4),
            },
        }

    async def evaluate_batch(self, dataset: List[Dict]) -> Dict:
        if not dataset:
            return {"avg_hit_rate": 0.0, "avg_mrr": 0.0}

        hit_rates = [
            self.calculate_hit_rate(case.get("expected_retrieval_ids", []), case.get("retrieved_ids", []), top_k=3)
            for case in dataset
        ]
        mrrs = [
            self.calculate_mrr(case.get("expected_retrieval_ids", []), case.get("retrieved_ids", []))
            for case in dataset
        ]
        return {
            "avg_hit_rate": self._safe_average(hit_rates),
            "avg_mrr": self._safe_average(mrrs),
        }
