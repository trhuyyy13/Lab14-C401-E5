import asyncio
import json
import os
import time
from engine.runner import BenchmarkRunner
from agent.main_agent import MainAgent
from engine.retrieval_eval import RetrievalEvaluator
from engine.llm_judge import LLMJudge


def _load_dataset(path: str):
    if not os.path.exists(path):
        print("❌ Thiếu data/golden_set.jsonl. Hãy chạy 'python data/synthetic_gen.py' trước.")
        return []

    with open(path, "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if not dataset:
        print("❌ File data/golden_set.jsonl rỗng. Hãy tạo ít nhất 1 test case.")
    return dataset


def _compute_summary(agent_version: str, results):
    total = len(results)
    pass_count = sum(1 for r in results if r["status"] == "pass")

    metric_extractors = {
        "avg_score": lambda r: r["judge"]["final_score"],
        "hit_rate": lambda r: r["ragas"]["retrieval"]["hit_rate"],
        "mrr": lambda r: r["ragas"]["retrieval"]["mrr"],
        "agreement_rate": lambda r: r["judge"]["agreement_rate"],
        "faithfulness": lambda r: r["ragas"]["faithfulness"],
        "relevancy": lambda r: r["ragas"]["relevancy"],
        "avg_latency_sec": lambda r: r["latency"],
        "avg_tokens": lambda r: r["metadata"]["agent"].get("tokens_used", 0),
    }

    metric_values = {
        name: sum(extractor(result) for result in results) / total
        for name, extractor in metric_extractors.items()
    }
    metric_values["pass_rate"] = round(pass_count / total, 4)
    metric_values["estimated_cost_usd"] = round((metric_values["avg_tokens"] * total / 1000) * 0.0003, 6)

    rounded_metrics = {}
    for key, value in metric_values.items():
        if key == "avg_tokens":
            rounded_metrics[key] = round(value, 2)
        elif key == "estimated_cost_usd":
            rounded_metrics[key] = round(value, 6)
        else:
            rounded_metrics[key] = round(value, 4)

    return {
        "metadata": {
            "version": agent_version,
            "total": total,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "metrics": rounded_metrics,
    }


def _is_hard_gate_pass(summary):
    metrics = summary["metrics"]
    return (
        metrics["hit_rate"] >= 0.70
        and metrics["agreement_rate"] >= 0.50
        and metrics["avg_latency_sec"] <= 2.0
    )

async def run_benchmark_with_results(agent_version: str):
    print(f"🚀 Khởi động Benchmark cho {agent_version}...")

    dataset = _load_dataset("data/golden_set.jsonl")
    if not dataset:
        return None, None

    retrieval_evaluator = RetrievalEvaluator()
    judge = LLMJudge()

    agent_key = "v2" if "V2" in agent_version else "v1"
    runner = BenchmarkRunner(MainAgent(version=agent_key), retrieval_evaluator, judge)
    results = await runner.run_all(dataset)
    summary = _compute_summary(agent_version, results)
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

    hard_gate_pass = _is_hard_gate_pass(v2_summary)

    if delta > 0 and hard_gate_pass:
        print("✅ QUYẾT ĐỊNH: CHẤP NHẬN BẢN CẬP NHẬT (APPROVE)")
    else:
        print("❌ QUYẾT ĐỊNH: TỪ CHỐI (BLOCK RELEASE)")

if __name__ == "__main__":
    asyncio.run(main())
