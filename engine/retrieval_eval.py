from typing import List, Dict


class RetrievalEvaluator:
    def __init__(self):
        pass

    def calculate_retrieval_accuracy(self, expected_ids: List[str], retrieved_ids: List[str]) -> float:
        """
        Retrieval Accuracy (top-1): 1.0 nếu phần tử đầu tiên của retrieved_ids thuộc expected_ids.
        Với case out-of-context (expected_ids rỗng), accuracy = 1.0 nếu retrieval rỗng.
        """
        if not expected_ids:
            return 1.0 if not retrieved_ids else 0.0
        if not retrieved_ids:
            return 0.0
        return 1.0 if retrieved_ids[0] in expected_ids else 0.0

    def calculate_hit_rate(self, expected_ids: List[str], retrieved_ids: List[str], top_k: int = 3) -> float:
        """
        Trả về 1.0 nếu ít nhất một expected_id xuất hiện trong top_k retrieved_ids, ngược lại 0.0.
        Với case out-of-context (expected_ids rỗng), trả về 1.0 nếu retrieval cũng rỗng.
        """
        if not expected_ids:
            return 1.0 if not retrieved_ids else 0.0

        top_retrieved = retrieved_ids[:top_k]
        hit = any(doc_id in top_retrieved for doc_id in expected_ids)
        return 1.0 if hit else 0.0

    def calculate_mrr(self, expected_ids: List[str], retrieved_ids: List[str]) -> float:
        """
        Tìm vị trí đầu tiên của expected_id trong retrieved_ids.
        MRR = 1 / position (vị trí 1-indexed). Nếu không thấy thì là 0.
        Với case out-of-context (expected_ids rỗng), MRR = 1.0 nếu retrieval rỗng.
        """
        if not expected_ids:
            return 1.0 if not retrieved_ids else 0.0

        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in expected_ids:
                return 1.0 / (i + 1)
        return 0.0

    async def evaluate_batch(self, dataset: List[Dict]) -> Dict:
        """
        Chạy eval cho toàn bộ bộ dữ liệu.
        Dataset cần có trường 'expected_retrieval_ids' và Agent trả về 'retrieved_ids'.
        """
        if not dataset:
            return {
                "retrieval_accuracy": 0.0,
                "hit_rate": 0.0,
                "average_hit_rate": 0.0,
                "mrr": 0.0,
                "details": [],
            }

        retrieval_accuracy_scores: List[float] = []
        hit_scores: List[float] = []
        mrr_scores: List[float] = []
        details: List[Dict] = []

        for item in dataset:
            expected_ids = item.get("expected_retrieval_ids", [])
            retrieved_ids = item.get("retrieved_ids", [])
            retrieval_accuracy = self.calculate_retrieval_accuracy(expected_ids, retrieved_ids)
            hit = self.calculate_hit_rate(expected_ids, retrieved_ids)
            mrr = self.calculate_mrr(expected_ids, retrieved_ids)

            retrieval_accuracy_scores.append(retrieval_accuracy)
            hit_scores.append(hit)
            mrr_scores.append(mrr)
            details.append(
                {
                    "id": item.get("id"),
                    "retrieval_accuracy": retrieval_accuracy,
                    "hit_rate": hit,
                    "mrr": mrr,
                    "expected_retrieval_ids": expected_ids,
                    "retrieved_ids": retrieved_ids,
                }
            )

        return {
            "retrieval_accuracy": sum(retrieval_accuracy_scores) / len(retrieval_accuracy_scores),
            "hit_rate": sum(hit_scores) / len(hit_scores),
            "average_hit_rate": sum(hit_scores) / len(hit_scores),
            "mrr": sum(mrr_scores) / len(mrr_scores),
            "details": details,
        }
