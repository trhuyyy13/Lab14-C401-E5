import asyncio
import json
import os
import re
import time
from typing import Dict, List
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

from engine.runner import BenchmarkRunner
from engine.retrieval_eval import RetrievalEvaluator
from agent.main_agent import MainAgent

class ExpertEvaluator:
    def __init__(self):
        root_dir = Path(__file__).resolve().parent
        load_dotenv(root_dir / ".env")
        api_key = (
            os.getenv("OPENAI_API_KEY")
            or os.getenv("OPENAIKEY")
            or os.getenv("OpenAIKEY")
        )
        if not api_key:
            raise ValueError(
                "Không tìm thấy OpenAI key. Hãy set OPENAI_API_KEY (hoặc OpenAIKEY) trong .env"
            )
        self.eval_model = os.getenv("EVAL_MODEL", "gpt-4o-mini")
        self.client = AsyncOpenAI(api_key=api_key)
        self.retrieval_eval = RetrievalEvaluator()

    async def score(self, case, resp):
        expected_ids = case.get("expected_retrieval_ids", [])
        retrieved_ids = resp.get("metadata", {}).get("retrieved_ids", [])

        hit_rate = self.retrieval_eval.calculate_hit_rate(expected_ids, retrieved_ids, top_k=3)
        mrr = self.retrieval_eval.calculate_mrr(expected_ids, retrieved_ids)
        top1_accuracy = self.retrieval_eval.calculate_top1_accuracy(expected_ids, retrieved_ids)

        question = case.get("question", "")
        expected_answer = case.get("expected_answer", "")
        answer = resp.get("answer", "")
        contexts = resp.get("contexts", [])
        context_block = "\n\n".join(
            [f"[Context {idx+1}] {ctx}" for idx, ctx in enumerate(contexts)]
        )

        faithfulness = 0.85 if mrr > 0 else 0.45
        relevancy = 0.9 if hit_rate > 0 else 0.5

        try:
            judge_resp = await self.client.chat.completions.create(
                model=self.eval_model,
                temperature=0.0,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Bạn là evaluator cho QA pháp lý. Trả về JSON hợp lệ với keys "
                            "faithfulness và relevancy (giá trị float từ 0 đến 1)."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Question: {question}\n"
                            f"Expected Answer: {expected_answer}\n"
                            f"Agent Answer: {answer}\n"
                            f"Contexts:\n{context_block}\n\n"
                            "Đánh giá:\n"
                            "- faithfulness: mức độ câu trả lời bám theo contexts\n"
                            "- relevancy: mức độ trả lời đúng trọng tâm question"
                        ),
                    },
                ],
            )
            parsed = json.loads(judge_resp.choices[0].message.content or "{}")
            faithfulness = float(parsed.get("faithfulness", faithfulness))
            relevancy = float(parsed.get("relevancy", relevancy))
            faithfulness = max(0.0, min(1.0, faithfulness))
            relevancy = max(0.0, min(1.0, relevancy))
        except Exception:
            pass

        return {
            "faithfulness": faithfulness,
            "relevancy": relevancy,
            "retrieval": {"hit_rate": hit_rate, "mrr": mrr, "top1_accuracy": top1_accuracy}
        }

class MultiModelJudge:
    def __init__(self):
        root_dir = Path(__file__).resolve().parent
        load_dotenv(root_dir / ".env")
        api_key = (
            os.getenv("OPENAI_API_KEY")
            or os.getenv("OPENAIKEY")
            or os.getenv("OpenAIKEY")
        )
        if not api_key:
            raise ValueError(
                "Không tìm thấy OpenAI key. Hãy set OPENAI_API_KEY (hoặc OpenAIKEY) trong .env"
            )

        self.judge_model_a = os.getenv("JUDGE_MODEL_A", "gpt-4o-mini")
        self.judge_model_b = os.getenv("JUDGE_MODEL_B", "gpt-4o")
        self.client = AsyncOpenAI(api_key=api_key)

    async def _score_with_model(self, model_name: str, question: str, answer: str, ground_truth: str):
        response = await self.client.chat.completions.create(
            model=model_name,
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Bạn là judge cho QA pháp lý. Trả về JSON với keys: score (1-5), reasoning (string)."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question: {question}\n"
                        f"Ground Truth: {ground_truth}\n"
                        f"Answer: {answer}\n\n"
                        "Chấm score theo độ đúng, đủ và rõ ràng so với Ground Truth."
                    ),
                },
            ],
        )

        parsed = json.loads(response.choices[0].message.content or "{}")
        score = float(parsed.get("score", 3.0))
        score = max(1.0, min(5.0, score))
        reasoning = str(parsed.get("reasoning", "No reasoning provided."))
        return score, reasoning

    async def evaluate_multi_judge(self, q, a, gt):
        score_a, reasoning_a = await self._score_with_model(self.judge_model_a, q, a, gt)
        score_b, reasoning_b = await self._score_with_model(self.judge_model_b, q, a, gt)
        final_score = (score_a + score_b) / 2.0
        agreement_rate = max(0.0, 1.0 - (abs(score_a - score_b) / 4.0))

        return {
            "final_score": final_score,
            "agreement_rate": agreement_rate,
            "individual_scores": {
                self.judge_model_a: score_a,
                self.judge_model_b: score_b,
            },
            "reasoning": f"JudgeA: {reasoning_a} | JudgeB: {reasoning_b}",
        }


def _safe_avg(values: List[float]) -> float:
    return (sum(values) / len(values)) if values else 0.0


def _build_summary(agent_version: str, results: List[Dict]) -> Dict:
    total = len(results)
    latencies = [r.get("latency", 0.0) for r in results]
    judge_scores = [r.get("judge", {}).get("final_score", 0.0) for r in results]
    agreements = [r.get("judge", {}).get("agreement_rate", 0.0) for r in results]

    hit_rates = [r.get("ragas", {}).get("retrieval", {}).get("hit_rate", 0.0) for r in results]
    mrr_scores = [r.get("ragas", {}).get("retrieval", {}).get("mrr", 0.0) for r in results]
    top1_scores = [r.get("ragas", {}).get("retrieval", {}).get("top1_accuracy", 0.0) for r in results]
    faithfulness_scores = [r.get("ragas", {}).get("faithfulness", 0.0) for r in results]

    final_answer_accuracy = (
        sum(1 for score in judge_scores if score >= 4.0) / total if total else 0.0
    )
    hallucination_rate = (
        sum(1 for score in faithfulness_scores if score < 0.7) / total if total else 0.0
    )

    total_tokens = sum(
        r.get("agent_metadata", {}).get("tokens_used", 0) for r in results
    )
    cost_per_1k_tokens = float(os.getenv("COST_PER_1K_TOKENS_USD", "0.0003"))
    total_cost = (total_tokens / 1000.0) * cost_per_1k_tokens
    avg_cost_per_case = (total_cost / total) if total else 0.0

    average_score = _safe_avg(judge_scores)
    user_satisfaction_score = (average_score / 5.0) * 100.0 if total else 0.0

    return {
        "metadata": {
            "version": agent_version,
            "total": total,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "metrics": {
            "retrieval_accuracy": _safe_avg(top1_scores),
            "hit_rate": _safe_avg(hit_rates),
            "average_hit_rate": _safe_avg(hit_rates),
            "mrr": _safe_avg(mrr_scores),
            "final_answer_accuracy": final_answer_accuracy,
            "hallucination_rate": hallucination_rate,
            "average_score": average_score,
            "avg_score": average_score,
            "latency": _safe_avg(latencies),
            "cost": total_cost,
            "avg_cost_per_case": avg_cost_per_case,
            "user_satisfaction_score": user_satisfaction_score,
            "agreement_rate": _safe_avg(agreements),
        },
    }


def _quality_index(summary: Dict) -> float:
    metrics = summary.get("metrics", {})
    avg_score_norm = metrics.get("avg_score", 0.0) / 5.0
    hit_rate = metrics.get("hit_rate", 0.0)
    mrr = metrics.get("mrr", 0.0)
    return (0.5 * avg_score_norm) + (0.3 * hit_rate) + (0.2 * mrr)

async def run_benchmark_with_results(agent_version: str, agent: MainAgent):
    print(f"🚀 Khởi động Benchmark cho {agent_version}...")

    if not os.path.exists("data/golden_set.jsonl"):
        print("❌ Thiếu data/golden_set.jsonl. Hãy chạy 'python data/synthetic_gen.py' trước.")
        return None, None

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if not dataset:
        print("❌ File data/golden_set.jsonl rỗng. Hãy tạo ít nhất 1 test case.")
        return None, None

    runner = BenchmarkRunner(agent, ExpertEvaluator(), MultiModelJudge())
    results = await runner.run_all(dataset)
    summary = _build_summary(agent_version, results)
    return results, summary

async def run_benchmark(version, agent: MainAgent):
    _, summary = await run_benchmark_with_results(version, agent)
    return summary

async def main():
    v1_agent = MainAgent(retrieval_mode="baseline")
    v2_agent = MainAgent(retrieval_mode="optimized")

    v1_summary = await run_benchmark("Agent_V1_Base", v1_agent)
    v2_results, v2_summary = await run_benchmark_with_results("Agent_V2_Optimized", v2_agent)
    
    if not v1_summary or not v2_summary:
        print("❌ Không thể chạy Benchmark. Kiểm tra lại data/golden_set.jsonl.")
        return

    print("\n📊 --- KẾT QUẢ SO SÁNH (REGRESSION) ---")
    score_delta = v2_summary["metrics"]["avg_score"] - v1_summary["metrics"]["avg_score"]
    hit_delta = v2_summary["metrics"]["hit_rate"] - v1_summary["metrics"]["hit_rate"]
    mrr_delta = v2_summary["metrics"]["mrr"] - v1_summary["metrics"]["mrr"]
    retrieval_acc_delta = (
        v2_summary["metrics"]["retrieval_accuracy"] - v1_summary["metrics"]["retrieval_accuracy"]
    )

    v1_qi = _quality_index(v1_summary)
    v2_qi = _quality_index(v2_summary)
    quality_delta = v2_qi - v1_qi

    print(f"V1 Score: {v1_summary['metrics']['avg_score']}")
    print(f"V2 Score: {v2_summary['metrics']['avg_score']}")
    print(f"Score Delta: {'+' if score_delta >= 0 else ''}{score_delta:.4f}")
    print(f"HitRate Delta: {'+' if hit_delta >= 0 else ''}{hit_delta:.4f}")
    print(f"MRR Delta: {'+' if mrr_delta >= 0 else ''}{mrr_delta:.4f}")
    print(f"RetrievalAcc Delta: {'+' if retrieval_acc_delta >= 0 else ''}{retrieval_acc_delta:.4f}")
    print(f"Quality Index Delta: {'+' if quality_delta >= 0 else ''}{quality_delta:.4f}")

    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)

    if quality_delta > 0:
        print("✅ QUYẾT ĐỊNH: CHẤP NHẬN BẢN CẬP NHẬT (APPROVE)")
    else:
        print("❌ QUYẾT ĐỊNH: TỪ CHỐI (BLOCK RELEASE)")

if __name__ == "__main__":
    asyncio.run(main())
