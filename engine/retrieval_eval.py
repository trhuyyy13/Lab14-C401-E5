from typing import List, Dict

class RetrievalEvaluator:
    def __init__(self):
        pass

    def calculate_top1_accuracy(self, expected_ids: List[str], retrieved_ids: List[str]) -> float:
        if not expected_ids or not retrieved_ids:
            return 0.0
        return 1.0 if retrieved_ids[0] in expected_ids else 0.0

    def calculate_hit_rate(self, expected_ids: List[str], retrieved_ids: List[str], top_k: int = 3) -> float:
        """
        TODO: Tính toán xem ít nhất 1 trong expected_ids có nằm trong top_k của retrieved_ids không.
        """
        top_retrieved = retrieved_ids[:top_k]
        hit = any(doc_id in top_retrieved for doc_id in expected_ids)
        return 1.0 if hit else 0.0

    def calculate_mrr(self, expected_ids: List[str], retrieved_ids: List[str]) -> float:
        """
        TODO: Tính Mean Reciprocal Rank.
        Tìm vị trí đầu tiên của một expected_id trong retrieved_ids.
        MRR = 1 / position (vị trí 1-indexed). Nếu không thấy thì là 0.
        """
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
            return {"avg_hit_rate": 0.0, "avg_mrr": 0.0, "avg_top1_accuracy": 0.0}

        hit_rates = []
        mrr_scores = []
        top1_scores = []

        for item in dataset:
            expected_ids = item.get("expected_retrieval_ids", [])
            retrieved_ids = item.get("retrieved_ids", [])
            hit_rates.append(self.calculate_hit_rate(expected_ids, retrieved_ids))
            mrr_scores.append(self.calculate_mrr(expected_ids, retrieved_ids))
            top1_scores.append(self.calculate_top1_accuracy(expected_ids, retrieved_ids))

        total = len(dataset)
        return {
            "avg_hit_rate": sum(hit_rates) / total,
            "avg_mrr": sum(mrr_scores) / total,
            "avg_top1_accuracy": sum(top1_scores) / total,
        }
