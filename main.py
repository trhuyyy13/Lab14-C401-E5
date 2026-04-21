import asyncio
import json
import os
import re
import time
from agent.main_agent import MainAgent
from engine.llm_judge import LLMJudge
from engine.retrieval_eval import RetrievalEvaluator
from engine.runner import BenchmarkRunner

class ExpertEvaluator:
    def __init__(self):
        self.retrieval_evaluator = RetrievalEvaluator()

    def _tokenize(self, text):
        return re.findall(r"\w+", text.lower(), flags=re.UNICODE)

    def _similarity(self, reference: str, candidate: str) -> float:
        ref_tokens = set(self._tokenize(reference))
        cand_tokens = set(self._tokenize(candidate))
        if not ref_tokens:
            return 0.0
        return len(ref_tokens.intersection(cand_tokens)) / len(ref_tokens)

    async def score(self, case, resp):
        rel = self._similarity(case.get("expected_answer", ""), resp.get("answer", ""))
        faithfulness = min(1.0, rel + 0.1)
        relevancy = rel
        retrieval = self.retrieval_evaluator.evaluate_case(
            case.get("expected_retrieval_ids", []),
            resp.get("retrieved_ids", []),
            top_k=3,
        )
        return {
            "faithfulness": round(faithfulness, 3),
            "relevancy": round(relevancy, 3),
            "retrieval": retrieval,
        }

def _build_summary(results, agent_version):
    total = len(results)
    if total == 0:
        return {
            "metadata": {"version": agent_version, "total": 0, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")},
            "metrics": {},
        }

    total_tokens = sum(r.get("token_usage", 0) for r in results)
    total_cost = sum(r.get("estimated_cost_usd", 0.0) for r in results)
    avg_latency = sum(r.get("latency", 0.0) for r in results) / total

    return {
        "metadata": {
            "version": agent_version,
            "total": total,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "metrics": {
            "avg_score": sum(r["judge"]["final_score"] for r in results) / total,
            "hit_rate": sum(r["ragas"]["retrieval"]["hit_rate"] for r in results) / total,
            "avg_mrr": sum(r["ragas"]["retrieval"]["mrr"] for r in results) / total,
            "agreement_rate": sum(r["judge"]["agreement_rate"] for r in results) / total,
            "pass_rate": sum(1 for r in results if r["status"] == "pass") / total,
            "avg_faithfulness": sum(r["ragas"]["faithfulness"] for r in results) / total,
            "avg_relevancy": sum(r["ragas"]["relevancy"] for r in results) / total,
            "avg_latency_sec": avg_latency,
            "total_tokens": total_tokens,
            "avg_tokens": total_tokens / total,
            "total_cost_usd": total_cost,
            "cost_per_eval_usd": total_cost / total,
        },
    }


def _release_gate(v1_summary, v2_summary):
    m1 = v1_summary["metrics"]
    m2 = v2_summary["metrics"]
    score_delta = m2["avg_score"] - m1["avg_score"]
    # Smooth latency ratio to avoid noisy gate decisions on short benchmarks.
    latency_floor = 0.02
    latency_ratio = (m2["avg_latency_sec"] + latency_floor) / (m1["avg_latency_sec"] + latency_floor)
    cost_ratio = m2["cost_per_eval_usd"] / max(m1["cost_per_eval_usd"], 1e-9)

    approve = (
        score_delta >= -0.05
        and m2["hit_rate"] >= m1["hit_rate"] - 0.02
        and latency_ratio <= 1.35
        and cost_ratio <= 1.20
    )

    return {
        "approve": approve,
        "score_delta": round(score_delta, 4),
        "latency_ratio": round(latency_ratio, 4),
        "cost_ratio": round(cost_ratio, 4),
    }

async def run_benchmark_with_results(agent_version: str, top_k: int):
    print(f"🚀 Khởi động Benchmark cho {agent_version}...")

    if not os.path.exists("data/golden_set.jsonl"):
        print("❌ Thiếu data/golden_set.jsonl. Hãy chạy 'python data/synthetic_gen.py' trước.")
        return None, None

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if not dataset:
        print("❌ File data/golden_set.jsonl rỗng. Hãy tạo ít nhất 1 test case.")
        return None, None

    runner = BenchmarkRunner(MainAgent(top_k=top_k), ExpertEvaluator(), LLMJudge())
    results = await runner.run_all(dataset)
    summary = _build_summary(results, agent_version)
    return results, summary

async def run_benchmark(version):
    _, summary = await run_benchmark_with_results(version, top_k=3)
    return summary

async def main():
    _, v1_summary = await run_benchmark_with_results("Agent_V1_Base", top_k=1)
    
    # V2 retrieval sâu hơn với top_k lớn hơn
    v2_results, v2_summary = await run_benchmark_with_results("Agent_V2_Optimized", top_k=3)
    
    if not v1_summary or not v2_summary:
        print("❌ Không thể chạy Benchmark. Kiểm tra lại data/golden_set.jsonl.")
        return

    print("\n📊 --- KẾT QUẢ SO SÁNH (REGRESSION) ---")
    gate = _release_gate(v1_summary, v2_summary)
    delta = gate["score_delta"]
    print(f"V1 Score: {v1_summary['metrics']['avg_score']}")
    print(f"V2 Score: {v2_summary['metrics']['avg_score']}")
    print(f"Delta: {'+' if delta >= 0 else ''}{delta:.2f}")
    print(f"Latency Ratio (V2/V1): {gate['latency_ratio']:.2f}")
    print(f"Cost Ratio (V2/V1): {gate['cost_ratio']:.2f}")

    v2_summary["regression"] = {
        "base_version": v1_summary["metadata"]["version"],
        "candidate_version": v2_summary["metadata"]["version"],
        **gate,
    }

    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)

    if gate["approve"]:
        print("✅ QUYẾT ĐỊNH: CHẤP NHẬN BẢN CẬP NHẬT (APPROVE)")
    else:
        print("❌ QUYẾT ĐỊNH: TỪ CHỐI (BLOCK RELEASE)")

if __name__ == "__main__":
    asyncio.run(main())
