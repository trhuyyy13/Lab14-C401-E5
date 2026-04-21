import asyncio
import time
from typing import List, Dict

# Giá ước tính USD/1M tokens (gpt-4o-mini input+output blended)
GPT4O_MINI_COST_PER_1M = 0.30  # $0.30 / 1M tokens

class BenchmarkRunner:
    def __init__(self, agent, evaluator, judge):
        self.agent = agent
        self.evaluator = evaluator
        self.judge = judge

    async def run_single_test(self, test_case: Dict) -> Dict:
        start_time = time.perf_counter()
        
        # 1. Gọi Agent
        response = await self.agent.query(test_case["question"])
        latency = time.perf_counter() - start_time
        
        # 2. Chạy RAGAS metrics
        ragas_scores = await self.evaluator.score(test_case, response)
        
        # 3. Chạy Multi-Judge
        judge_result = await self.judge.evaluate_multi_judge(
            test_case["question"], 
            response["answer"], 
            test_case["expected_answer"]
        )
        
        tokens_used = response.get("metadata", {}).get("tokens_used", 0)
        cost_usd = tokens_used * GPT4O_MINI_COST_PER_1M / 1_000_000

        # User Satisfaction Score: weighted judge sub-scores
        detail_a = judge_result.get("detail", {}).get("gpt-4o", {})
        acc   = float(detail_a.get("accuracy",      judge_result["final_score"]))
        comp  = float(detail_a.get("completeness",  judge_result["final_score"]))
        prof  = float(detail_a.get("professionalism", judge_result["final_score"]))
        uss   = round(0.5 * acc + 0.3 * comp + 0.2 * prof, 2)

        # Hallucination flag: agent gave non-refusal answer but retrieval missed
        hit   = ragas_scores["retrieval"]["hit_rate"]
        refusal_keywords = ["không tìm thấy", "không có thông tin", "ngoài phạm vi", "i don't"]
        is_refusal = any(kw in response["answer"].lower() for kw in refusal_keywords)
        hallucination = (hit == 0.0 and not is_refusal
                         and bool(test_case.get("expected_retrieval_ids")))

        return {
            "test_case": test_case["question"],
            "test_case_metadata": test_case.get("metadata", {}),
            "expected_answer": test_case.get("expected_answer", ""),
            "agent_response": response["answer"],
            "latency": latency,
            "tokens_used": tokens_used,
            "cost_usd": cost_usd,
            "hallucination": hallucination,
            "user_satisfaction_score": uss,
            "ragas": ragas_scores,
            "judge": judge_result,
            "status": "fail" if judge_result["final_score"] < 3 else "pass"
        }

    async def run_all(self, dataset: List[Dict], batch_size: int = 5) -> List[Dict]:
        """
        Chạy song song bằng asyncio.gather với giới hạn batch_size để không bị Rate Limit.
        """
        results = []
        for i in range(0, len(dataset), batch_size):
            batch = dataset[i:i + batch_size]
            tasks = [self.run_single_test(case) for case in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
        return results
