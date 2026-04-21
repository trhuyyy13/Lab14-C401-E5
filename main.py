import asyncio
import json
import os
import time
from engine.runner import BenchmarkRunner
from agent.main_agent import MainAgent
from engine.retrieval_eval import RetrievalEvaluator
from engine.llm_judge import LLMJudge

async def run_benchmark_with_results(agent_version: str):
    print(f"🚀 Khởi động Benchmark cho {agent_version}...")

    if not os.path.exists("data/golden_set.jsonl"):
        print("❌ Thiếu data/golden_set.jsonl. Hãy chạy 'python data/synthetic_gen.py' trước.")
        return None, None

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if not dataset:
        print("❌ File data/golden_set.jsonl rỗng. Hãy tạo ít nhất 1 test case.")
        return None, None

    retrieval_evaluator = RetrievalEvaluator()
    judge = LLMJudge()

    agent_key = "v2" if "V2" in agent_version else "v1"
    runner = BenchmarkRunner(MainAgent(version=agent_key), retrieval_evaluator, judge)
    results = await runner.run_all(dataset)

    total = len(results)
    pass_count = sum(1 for r in results if r["status"] == "pass")

    avg_score = sum(r["judge"]["final_score"] for r in results) / total
    hit_rate = sum(r["ragas"]["retrieval"]["hit_rate"] for r in results) / total
    mrr = sum(r["ragas"]["retrieval"]["mrr"] for r in results) / total
    agreement_rate = sum(r["judge"]["agreement_rate"] for r in results) / total
    avg_faithfulness = sum(r["ragas"]["faithfulness"] for r in results) / total
    avg_relevancy = sum(r["ragas"]["relevancy"] for r in results) / total
    avg_latency = sum(r["latency"] for r in results) / total
    avg_tokens = sum(r["metadata"]["agent"].get("tokens_used", 0) for r in results) / total

    total_cost_usd = round((avg_tokens * total / 1000) * 0.0003, 6)

    summary = {
        "metadata": {"version": agent_version, "total": total, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")},
        "metrics": {
            "pass_rate": round(pass_count / total, 4),
            "avg_score": round(avg_score, 4),
            "hit_rate": round(hit_rate, 4),
            "mrr": round(mrr, 4),
            "agreement_rate": round(agreement_rate, 4),
            "faithfulness": round(avg_faithfulness, 4),
            "relevancy": round(avg_relevancy, 4),
            "avg_latency_sec": round(avg_latency, 4),
            "avg_tokens": round(avg_tokens, 2),
            "estimated_cost_usd": total_cost_usd,
        },
    }
    return results, summary

async def run_benchmark(version):
    _, summary = await run_benchmark_with_results(version)
    return summary

async def main():
    v1_summary = await run_benchmark("Agent_V1_Base")

    v2_results, v2_summary = await run_benchmark_with_results("Agent_V2_Optimized")

    if not v1_summary or not v2_summary:
        print("❌ Không thể chạy Benchmark. Kiểm tra lại data/golden_set.jsonl.")
        return

    print("\n📊 --- KẾT QUẢ SO SÁNH (REGRESSION) ---")
    delta = v2_summary["metrics"]["avg_score"] - v1_summary["metrics"]["avg_score"]
    print(f"V1 Score: {v1_summary['metrics']['avg_score']}")
    print(f"V2 Score: {v2_summary['metrics']['avg_score']}")
    print(f"Delta: {'+' if delta >= 0 else ''}{delta:.2f}")

    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)

    hard_gate_pass = (
        v2_summary["metrics"]["hit_rate"] >= 0.70
        and v2_summary["metrics"]["agreement_rate"] >= 0.50
        and v2_summary["metrics"]["avg_latency_sec"] <= 2.0
    )

    if delta > 0 and hard_gate_pass:
        print("✅ QUYẾT ĐỊNH: CHẤP NHẬN BẢN CẬP NHẬT (APPROVE)")
    else:
        print("❌ QUYẾT ĐỊNH: TỪ CHỐI (BLOCK RELEASE)")

if __name__ == "__main__":
    asyncio.run(main())
