import asyncio
import os
import time
from typing import List, Dict
# Import other components...


class BenchmarkRunner:
    def __init__(self, agent, evaluator, judge):
        self.agent = agent
        self.evaluator = evaluator
        self.judge = judge

    async def run_single_test(self, test_case: Dict) -> Dict:
        start_time = time.perf_counter()

        # 1. Gọi Agent
        try:
            response = await self.agent.query(
                test_case["question"],
                test_case.get("expected_retrieval_ids", []),
            )
        except TypeError:
            # Backward compatibility cho agent chưa hỗ trợ expected_retrieval_ids.
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
        try:
            tokens_used = int(tokens_used)
        except (TypeError, ValueError):
            tokens_used = 0

        cost_per_1k_tokens = float(os.getenv("COST_PER_1K_TOKENS", "0.00015"))
        cost = (tokens_used / 1000.0) * cost_per_1k_tokens

        retrieval_hit = ragas_scores.get("retrieval", {}).get("hit_rate", 0.0)
        hallucination_rate = ragas_scores.get("hallucination_rate", 0.0)
        user_satisfaction_score = max(
            1.0,
            min(5.0, judge_result["final_score"] + 0.4 * retrieval_hit - 0.6 * hallucination_rate),
        )

        return {
            "id": test_case.get("id"),
            "test_case": test_case["question"],
            "agent_response": response["answer"],
            "latency": latency,
            "cost": round(cost, 8),
            "ragas": ragas_scores,
            "judge": judge_result,
            "user_satisfaction_score": round(user_satisfaction_score, 3),
            "retrieved_ids": response.get("retrieved_ids", []),
            "expected_retrieval_ids": test_case.get("expected_retrieval_ids", []),
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
