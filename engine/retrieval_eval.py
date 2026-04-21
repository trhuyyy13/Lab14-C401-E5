from typing import List, Dict

class RetrievalEvaluator:
    def __init__(self):
        self.default_top_k = 3

    def calculate_hit_rate(self, expected_ids: List[str], retrieved_ids: List[str], top_k: int = 3) -> float:
        """Return 1.0 if at least one expected id appears in top_k retrieved ids, else 0.0."""
        if not expected_ids or not retrieved_ids:
            return 0.0
        top_retrieved = retrieved_ids[:top_k]
        hit = any(doc_id in top_retrieved for doc_id in expected_ids)
        return 1.0 if hit else 0.0

    def calculate_mrr(self, expected_ids: List[str], retrieved_ids: List[str]) -> float:
        """Return reciprocal rank of first matched expected id; 0.0 when no match."""
        if not expected_ids or not retrieved_ids:
            return 0.0
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in expected_ids:
                return 1.0 / (i + 1)
        return 0.0

    def evaluate_case(self, expected_ids: List[str], retrieved_ids: List[str], top_k: int = 3) -> Dict:
        return {
            "hit_rate": self.calculate_hit_rate(expected_ids, retrieved_ids, top_k=top_k),
            "mrr": self.calculate_mrr(expected_ids, retrieved_ids),
            "top_k": top_k,
        }

    async def evaluate_batch(self, dataset: List[Dict]) -> Dict:
        """Evaluate retrieval metrics for records containing expected_retrieval_ids and retrieved_ids."""
        if not dataset:
            return {
                "avg_hit_rate": 0.0,
                "avg_mrr": 0.0,
                "total": 0,
                "per_case": [],
            }

        per_case = []
        hit_sum = 0.0
        mrr_sum = 0.0

        for record in dataset:
            expected_ids = record.get("expected_retrieval_ids", [])
            retrieved_ids = record.get("retrieved_ids", [])
            top_k = int(record.get("top_k", self.default_top_k))

            scores = self.evaluate_case(expected_ids, retrieved_ids, top_k=top_k)
            per_case.append(
                {
                    "question": record.get("question", ""),
                    "expected_retrieval_ids": expected_ids,
                    "retrieved_ids": retrieved_ids,
                    **scores,
                }
            )
            hit_sum += scores["hit_rate"]
            mrr_sum += scores["mrr"]

        total = len(dataset)
        return {
            "avg_hit_rate": hit_sum / total,
            "avg_mrr": mrr_sum / total,
            "total": total,
            "per_case": per_case,
        }
