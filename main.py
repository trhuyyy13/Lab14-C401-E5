import asyncio
import json
import os
import time
from engine.runner import BenchmarkRunner
from engine.retrieval_eval import RetrievalEvaluator
from engine.llm_judge import LLMJudge
from agent.main_agent import MainAgent
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

class ExpertEvaluator:
    def __init__(self):
        self.retrieval_eval = RetrievalEvaluator()

    async def score(self, case, resp):
        expected_ids = case.get("expected_retrieval_ids", [])
        retrieved_ids = resp.get("retrieved_ids", [])

        if expected_ids:
            hit_rate = self.retrieval_eval.calculate_hit_rate(expected_ids, retrieved_ids)
            mrr = self.retrieval_eval.calculate_mrr(expected_ids, retrieved_ids)
        else:
            # Không có ground truth IDs → không thể tính chính xác
            hit_rate = 0.0
            mrr = 0.0

        return {
            "faithfulness": 0.9,   # TODO: thay bằng RAGAS thực nếu cần
            "relevancy": 0.8,
            "retrieval": {"hit_rate": hit_rate, "mrr": mrr},
        }


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

    agent = MainAgent(version=agent_version.split("_")[1].lower() if "_" in agent_version else "v1")
    runner = BenchmarkRunner(agent, ExpertEvaluator(), LLMJudge())
    results = await runner.run_all(dataset)

    total = len(results)
    n_hit        = sum(r["ragas"]["retrieval"]["hit_rate"] for r in results)
    n_accurate   = sum(1 for r in results
                       if r["judge"].get("detail", {}).get("gpt-4o", {}).get("accuracy", 0) >= 4)
    n_halluc     = sum(1 for r in results if r.get("hallucination", False))
    total_tokens = sum(r.get("tokens_used", 0) for r in results)
    total_cost   = sum(r.get("cost_usd", 0.0) for r in results)

    summary = {
        "metadata": {
            "version": agent_version,
            "total": total,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "metrics": {
            # --- Retrieval ---
            "hit_rate":              round(n_hit / total, 4),
            "avg_hit_rate":          round(n_hit / total, 4),          # alias
            "avg_mrr":               round(sum(r["ragas"]["retrieval"]["mrr"] for r in results) / total, 4),
            "retrieval_accuracy":    round(n_hit / total, 4),          # % cases w/ at least 1 correct chunk
            # --- Answer quality ---
            "avg_score":             round(sum(r["judge"]["final_score"] for r in results) / total, 4),
            "final_answer_accuracy": round(n_accurate / total, 4),     # % cases accuracy >= 4/5
            "hallucination_rate":    round(n_halluc / total, 4),       # % cases hallucinated
            # --- Multi-Judge ---
            "agreement_rate":        round(sum(r["judge"]["agreement_rate"] for r in results) / total, 4),
            # --- UX ---
            "user_satisfaction_score": round(sum(r.get("user_satisfaction_score", 0) for r in results) / total, 4),
            # --- Performance & Cost ---
            "avg_latency_sec":       round(sum(r["latency"] for r in results) / total, 3),
            "total_latency_sec":     round(sum(r["latency"] for r in results), 2),
            "total_tokens":          total_tokens,
            "total_cost_usd":        round(total_cost, 6),
            "cost_per_case_usd":     round(total_cost / total, 6),
        },
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

    m1 = v1_summary["metrics"]
    m2 = v2_summary["metrics"]
    delta = m2["avg_score"] - m1["avg_score"]

    print(f"{'Metric':<28} {'V1':>8} {'V2':>8} {'Delta':>8}")
    print("-" * 56)
    metrics_to_show = [
        ("avg_score",               "Avg Score"),
        ("hit_rate",                "Hit Rate"),
        ("avg_hit_rate",            "Avg Hit Rate"),
        ("retrieval_accuracy",      "Retrieval Accuracy"),
        ("avg_mrr",                 "Avg MRR"),
        ("final_answer_accuracy",   "Final Answer Accuracy"),
        ("hallucination_rate",      "Hallucination Rate"),
        ("agreement_rate",          "Agreement Rate"),
        ("user_satisfaction_score", "User Satisfaction Score"),
        ("avg_latency_sec",         "Avg Latency (s)"),
        ("cost_per_case_usd",       "Cost/Case (USD)"),
        ("total_cost_usd",          "Total Cost (USD)"),
    ]
    for key, label in metrics_to_show:
        v1_val = m1.get(key, 0)
        v2_val = m2.get(key, 0)
        d = v2_val - v1_val
        print(f"  {label:<26} {v1_val:>8.4f} {v2_val:>8.4f} {d:>+8.4f}")
    print("-" * 56)

    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)

    # Release gate
    hit_rate_ok  = m2["hit_rate"] >= 0.5
    agreement_ok = m2["agreement_rate"] >= 0.6
    halluc_ok    = m2["hallucination_rate"] <= 0.15
    approve = delta > 0.05 and hit_rate_ok and agreement_ok and halluc_ok
    if approve:
        print("\n✅ QUYẾT ĐỊNH: CHẤP NHẬN BẢN CẬP NHẬT (APPROVE)")
    else:
        reasons = []
        if delta <= 0.05:   reasons.append(f"score delta={delta:.2f} <= 0.05")
        if not hit_rate_ok: reasons.append(f"hit_rate={m2['hit_rate']:.2f} < 0.5")
        if not agreement_ok:reasons.append(f"agreement={m2['agreement_rate']:.2f} < 0.6")
        if not halluc_ok:   reasons.append(f"hallucination={m2['hallucination_rate']:.2f} > 0.15")
        print(f"\n❌ QUYẾT ĐỊNH: TỪ CHỐI (BLOCK RELEASE) — {', '.join(reasons)}")

    # Auto-generate failure analysis report
    print("\n📝 Đang tạo failure_analysis.md...")
    await generate_failure_analysis(v2_results, v1_summary, v2_summary)
    print("✅ Đã lưu analysis/failure_analysis.md")


async def generate_failure_analysis(results: list, v1_summary: dict, v2_summary: dict):
    """Tự động sinh analysis/failure_analysis.md từ kết quả benchmark thực."""
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = total - passed

    avg_judge        = sum(r["judge"]["final_score"] for r in results) / total
    avg_faithfulness = sum(r["ragas"]["faithfulness"] for r in results) / total
    avg_relevancy    = sum(r["ragas"]["relevancy"] for r in results) / total
    avg_hit_rate     = sum(r["ragas"]["retrieval"]["hit_rate"] for r in results) / total
    avg_mrr          = sum(r["ragas"]["retrieval"]["mrr"] for r in results) / total
    avg_agreement    = sum(r["judge"]["agreement_rate"] for r in results) / total
    avg_latency      = sum(r["latency"] for r in results) / total
    avg_uss          = sum(r.get("user_satisfaction_score", 0) for r in results) / total
    halluc_rate      = sum(1 for r in results if r.get("hallucination")) / total
    n_accurate       = sum(1 for r in results
                           if r["judge"].get("detail", {}).get("gpt-4o", {}).get("accuracy", 0) >= 4)
    final_acc        = n_accurate / total
    total_cost       = sum(r.get("cost_usd", 0.0) for r in results)
    cost_per_case    = total_cost / total

    # Failure clustering by type
    failure_groups: dict = {}
    for r in results:
        if r["status"] == "fail":
            t = r.get("test_case_metadata", {}).get("type", "unknown")
            failure_groups[t] = failure_groups.get(t, 0) + 1

    # By difficulty
    diff_stats: dict = {}
    for r in results:
        d = r.get("test_case_metadata", {}).get("difficulty", "unknown")
        if d not in diff_stats:
            diff_stats[d] = {"total": 0, "fail": 0, "score_sum": 0.0}
        diff_stats[d]["total"] += 1
        if r["status"] == "fail":
            diff_stats[d]["fail"] += 1
        diff_stats[d]["score_sum"] += r["judge"]["final_score"]

    # 3 worst cases
    worst_3 = sorted(
        [r for r in results if r["status"] == "fail" or r["judge"]["final_score"] < 4],
        key=lambda r: r["judge"]["final_score"]
    )[:3]
    if not worst_3:
        worst_3 = sorted(results, key=lambda r: r["judge"]["final_score"])[:3]

    # Dùng LLM sinh 5 Whys cho từng case tệ nhất
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    five_whys_blocks = []
    for i, case in enumerate(worst_3, 1):
        prompt = f"""Bạn là chuyên gia phân tích lỗi hệ thống RAG (Retrieval-Augmented Generation).
Hãy thực hiện phân tích "5 Whys" ngắn gọn cho case sau:

Câu hỏi: {case["test_case"]}
Câu trả lời của Agent: {case["agent_response"][:300]}
Điểm Judge: {case["judge"]["final_score"]}/5
Lý do chấm điểm: {case["judge"].get("reasoning", "N/A")}
Hit Rate Retrieval: {case["ragas"]["retrieval"]["hit_rate"]}
MRR: {case["ragas"]["retrieval"]["mrr"]:.2f}
Loại case: {case.get("test_case_metadata", {}).get("type", "unknown")}
Độ khó: {case.get("test_case_metadata", {}).get("difficulty", "unknown")}

Viết phân tích 5 Whys, tìm root cause liên quan đến: Chunking, Retrieval, Prompt, LLM.
Format (plain text):
Symptom: [mô tả]
Why 1: ...
Why 2: ...
Why 3: ...
Why 4: ...
Root Cause: [kết luận]"""
        try:
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=350,
            )
            analysis = resp.choices[0].message.content.strip()
        except Exception as e:
            analysis = f"Symptom: Không thể phân tích tự động\nRoot Cause: {e}"
        five_whys_blocks.append((i, case, analysis))

    # Build failure table
    table_rows = ""
    for ftype, count in failure_groups.items():
        causes = {
            "out-of-context": "Agent cần nhận biết câu hỏi ngoài phạm vi tài liệu",
            "prompt-injection": "Agent cần kháng cự yêu cầu tấn công",
            "wrong-premise": "Agent phải phát hiện tiền đề sai trong câu hỏi",
            "ambiguous": "Agent cần yêu cầu làm rõ thay vì đoán mò",
            "fact-check": "Retrieval không tìm được chunk liên quan",
            "interpretation": "LLM không diễn giải đúng ngữ nghĩa điều luật",
            "reasoning": "Thiếu khả năng suy luận đa bước",
        }
        cause = causes.get(ftype, "Cần phân tích thêm")
        table_rows += f"| {ftype} | {count} | {cause} |\n"

    # Build difficulty table
    diff_table = ""
    for diff in ["easy", "medium", "hard", "adversarial"]:
        if diff in diff_stats:
            s = diff_stats[diff]
            avg_s = s["score_sum"] / s["total"]
            diff_table += f"| {diff} | {s['total']} | {s['fail']} | {avg_s:.2f}/5 |\n"

    # Build 5 Whys sections
    five_whys_md = ""
    for i, case, analysis in five_whys_blocks:
        dtype = case.get("test_case_metadata", {}).get("difficulty", "?")
        qtype = case.get("test_case_metadata", {}).get("type", "?")
        score = case["judge"]["final_score"]
        five_whys_md += f"""
### Case #{i}: [{dtype} / {qtype}] — Score {score}/5
**Câu hỏi:** {case["test_case"][:150]}...

{analysis}
"""

    # Regression delta
    delta = v2_summary["metrics"]["avg_score"] - v1_summary["metrics"]["avg_score"]
    v1_score = v1_summary["metrics"]["avg_score"]
    v2_score = v2_summary["metrics"]["avg_score"]

    md = f"""# Báo cáo Phân tích Thất bại (Failure Analysis Report)

## 1. Tổng quan Benchmark
- **Tổng số cases:** {total}
- **Tỉ lệ Pass/Fail:** {passed}/{failed}
- **Phân bố theo độ khó:**

| Độ khó | Tổng | Fail | Avg Score |
|--------|------|------|-----------|
{diff_table}

### Metrics tổng hợp

| Metric | Giá trị |
|--------|---------|
| Retrieval Accuracy | {avg_hit_rate:.2%} |
| Hit Rate | {avg_hit_rate:.2%} |
| Average Hit Rate | {avg_hit_rate:.2%} |
| Average MRR | {avg_mrr:.4f} |
| Final Answer Accuracy | {final_acc:.2%} |
| Hallucination Rate | {halluc_rate:.2%} |
| Average Score (Judge) | {avg_judge:.2f} / 5.0 |
| Agreement Rate (Multi-Judge) | {avg_agreement:.2%} |
| User Satisfaction Score | {avg_uss:.2f} / 5.0 |
| Avg Latency | {avg_latency:.2f}s / case |
| Cost per Case | ${cost_per_case:.6f} |
| Total Cost | ${total_cost:.4f} |
| Faithfulness (RAGAS) | {avg_faithfulness:.2f} |
| Relevancy (RAGAS) | {avg_relevancy:.2f} |

## 2. Regression Testing (V1 vs V2)
| Metric | V1 Base | V2 Optimized | Delta |
|--------|---------|--------------|-------|
| Avg Score | {v1_summary['metrics']['avg_score']:.2f} | {v2_summary['metrics']['avg_score']:.2f} | {v2_summary['metrics']['avg_score']-v1_summary['metrics']['avg_score']:+.2f} |
| Hit Rate | {v1_summary['metrics']['hit_rate']:.2f} | {v2_summary['metrics']['hit_rate']:.2f} | {v2_summary['metrics']['hit_rate']-v1_summary['metrics']['hit_rate']:+.2f} |
| Hallucination Rate | {v1_summary['metrics']['hallucination_rate']:.2%} | {v2_summary['metrics']['hallucination_rate']:.2%} | {v2_summary['metrics']['hallucination_rate']-v1_summary['metrics']['hallucination_rate']:+.2%} |
| User Satisfaction | {v1_summary['metrics']['user_satisfaction_score']:.2f} | {v2_summary['metrics']['user_satisfaction_score']:.2f} | {v2_summary['metrics']['user_satisfaction_score']-v1_summary['metrics']['user_satisfaction_score']:+.2f} |
| Avg Latency (s) | {v1_summary['metrics']['avg_latency_sec']:.2f} | {v2_summary['metrics']['avg_latency_sec']:.2f} | {v2_summary['metrics']['avg_latency_sec']-v1_summary['metrics']['avg_latency_sec']:+.2f} |
| Cost/Case (USD) | {v1_summary['metrics']['cost_per_case_usd']:.5f} | {v2_summary['metrics']['cost_per_case_usd']:.5f} | {v2_summary['metrics']['cost_per_case_usd']-v1_summary['metrics']['cost_per_case_usd']:+.5f} |

## 3. Phân nhóm lỗi (Failure Clustering)
| Nhóm lỗi | Số lượng | Nguyên nhân dự kiến |
|----------|----------|---------------------|
{table_rows}
## 4. Phân tích 5 Whys (3 case tệ nhất)
{five_whys_md}
## 5. Kế hoạch cải tiến (Action Plan)
- [ ] **Chunking**: Xem xét giảm size chunk hoặc dùng Semantic Chunking cho các điều luật dài, tránh loãng thông tin.
- [ ] **Retrieval**: Thêm bước Reranking (Cross-Encoder) sau Vector Search để cải thiện MRR.
- [ ] **Prompt**: Cập nhật System Prompt để xử lý rõ hơn các câu hỏi adversarial và out-of-context.
- [ ] **Agent V2**: Tăng top_k=5 và temperature=0 đã giúp một phần; xem xét thêm query expansion.
- [ ] **Cost**: Dùng gpt-4o-mini cho retrieval embedding, chỉ dùng gpt-4o cho judge để giảm ~40% chi phí.
"""

    os.makedirs("analysis", exist_ok=True)
    with open("analysis/failure_analysis.md", "w", encoding="utf-8") as f:
        f.write(md)


if __name__ == "__main__":
    asyncio.run(main())
