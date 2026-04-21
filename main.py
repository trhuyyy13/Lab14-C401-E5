import asyncio
import json
import os
import time
from typing import Dict
from engine.runner import BenchmarkRunner
from engine.llm_judge import LLMJudge
from engine.retrieval_eval import RetrievalEvaluator
from agent.main_agent import MainAgent


class ExpertEvaluator:
    def __init__(self):
        self.retrieval_eval = RetrievalEvaluator()

    @staticmethod
    def _token_overlap(a: str, b: str) -> float:
        set_a = set((a or "").lower().split())
        set_b = set((b or "").lower().split())
        if not set_b:
            return 0.0
        return len(set_a.intersection(set_b)) / max(1, len(set_b))

    @staticmethod
    def _is_abstain_answer(answer: str) -> bool:
        lower = (answer or "").lower()
        markers = [
            "không đủ thông tin",
            "không có dữ kiện",
            "không tìm thấy thông tin",
            "tôi không biết",
        ]
        return any(marker in lower for marker in markers)

    def _hallucination_rate(self, case: Dict, resp: Dict) -> float:
        answer = resp.get("answer", "")
        contexts = " ".join(resp.get("contexts", []))
        expected_answer = case.get("expected_answer", "")
        expected_ids = case.get("expected_retrieval_ids", [])

        # Out-of-context: nên từ chối trả lời, nếu không thì xem là hallucination.
        if not expected_ids:
            return 0.0 if self._is_abstain_answer(answer) else 1.0

        context_support = self._token_overlap(answer, contexts)
        gt_overlap = self._token_overlap(answer, expected_answer)
        if context_support < 0.08 and gt_overlap < 0.2:
            return 1.0
        if gt_overlap < 0.1:
            return 0.5
        return 0.0

    async def score(self, case, resp):
        expected_ids = case.get("expected_retrieval_ids", [])
        retrieved_ids = resp.get("retrieved_ids", [])
        retrieval_accuracy = self.retrieval_eval.calculate_retrieval_accuracy(
            expected_ids, retrieved_ids)
        hit_rate = self.retrieval_eval.calculate_hit_rate(
            expected_ids, retrieved_ids, top_k=3)
        mrr = self.retrieval_eval.calculate_mrr(expected_ids, retrieved_ids)
        final_answer_accuracy = self._token_overlap(
            resp.get("answer", ""), case.get("expected_answer", ""))
        hallucination_rate = self._hallucination_rate(case, resp)

        return {
            "faithfulness": round(final_answer_accuracy, 3),
            "relevancy": round(final_answer_accuracy, 3),
            "retrieval": {
                "retrieval_accuracy": retrieval_accuracy,
                "hit_rate": hit_rate,
                "average_hit_rate": hit_rate,
                "mrr": mrr,
            },
            "final_answer_accuracy": round(final_answer_accuracy, 3),
            "hallucination_rate": round(hallucination_rate, 3),
        }


async def run_benchmark_with_results(agent_version: str):
    print(f"🚀 Khởi động Benchmark cho {agent_version}...")

    if not os.path.exists("data/golden_set.jsonl"):
        print(
            "❌ Thiếu data/golden_set.jsonl. Hãy chạy 'python data/synthetic_gen.py' trước.")
        return None, None

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if not dataset:
        print("❌ File data/golden_set.jsonl rỗng. Hãy tạo ít nhất 1 test case.")
        return None, None

    runner = BenchmarkRunner(MainAgent(), ExpertEvaluator(), LLMJudge())
    results = await runner.run_all(dataset)

    total = len(results)
    avg_score = sum(r["judge"]["final_score"] for r in results) / total
    retrieval_accuracy = sum(r["ragas"]["retrieval"]["retrieval_accuracy"] for r in results) / total
    hit_rate = sum(r["ragas"]["retrieval"]["hit_rate"] for r in results) / total
    avg_hit_rate = sum(r["ragas"]["retrieval"]["average_hit_rate"] for r in results) / total
    final_answer_accuracy = sum(r["ragas"]["final_answer_accuracy"] for r in results) / total
    hallucination_rate = sum(r["ragas"]["hallucination_rate"] for r in results) / total
    avg_latency = sum(r["latency"] for r in results) / total
    total_cost = sum(r.get("cost", 0.0) for r in results)
    avg_cost = total_cost / total
    user_satisfaction_score = sum(r.get("user_satisfaction_score", 0.0) for r in results) / total

    summary = {
        "metadata": {"version": agent_version, "total": total, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")},
        "metrics": {
            "retrieval_accuracy": retrieval_accuracy,
            "hit_rate": hit_rate,
            "average_hit_rate": avg_hit_rate,
            "final_answer_accuracy": final_answer_accuracy,
            "hallucination_rate": hallucination_rate,
            "avg_score": avg_score,
            "average_score": avg_score,
            "latency": avg_latency,
            "avg_latency": avg_latency,
            "cost": total_cost,
            "average_cost": avg_cost,
            "user_satisfaction_score": user_satisfaction_score,
            "mrr": sum(r["ragas"]["retrieval"]["mrr"] for r in results) / total,
            "agreement_rate": sum(r["judge"]["agreement_rate"] for r in results) / total
        }
    }
    return results, summary


async def run_benchmark(version):
    _, summary = await run_benchmark_with_results(version)
    return summary


async def main():
    v1_summary = await run_benchmark("Agent_V1_Base")

    # Giả lập V2 có cải tiến (để test logic)
    v2_results, v2_summary = await run_benchmark_with_results("Agent_V2_Optimized")

    if not v1_summary or not v2_summary:
        print("❌ Không thể chạy Benchmark. Kiểm tra lại data/golden_set.jsonl.")
        return

    print("\n📊 --- KẾT QUẢ SO SÁNH (REGRESSION) ---")
    delta = v2_summary["metrics"]["avg_score"] - \
        v1_summary["metrics"]["avg_score"]
    print(f"V1 Score: {v1_summary['metrics']['avg_score']}")
    print(f"V2 Score: {v2_summary['metrics']['avg_score']}")
    print(f"Delta: {'+' if delta >= 0 else ''}{delta:.2f}")

    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)

    if delta > 0:
        print("✅ QUYẾT ĐỊNH: CHẤP NHẬN BẢN CẬP NHẬT (APPROVE)")
    else:
        print("❌ QUYẾT ĐỊNH: TỪ CHỐI (BLOCK RELEASE)")

if __name__ == "__main__":
    asyncio.run(main())
