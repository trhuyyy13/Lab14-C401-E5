import asyncio
import time
from typing import List, Dict

class BenchmarkRunner:
    def __init__(self, agent, evaluator, judge):
        self.agent = agent
        self.evaluator = evaluator
        self.judge = judge

    async def run_single_test(self, test_case: Dict) -> Dict:
        start_time = time.perf_counter()
        try:
            response = await self.agent.query(test_case["question"])
            latency = time.perf_counter() - start_time

            ragas_scores = await self.evaluator.score(test_case, response)

            judge_result = await self.judge.evaluate_multi_judge(
                test_case["question"],
                response["answer"],
                test_case.get("expected_answer", ""),
            )

            status = "fail" if judge_result["final_score"] < 3 else "pass"
        except Exception as exc:
            latency = time.perf_counter() - start_time
            response = {"answer": "", "retrieved_ids": [], "metadata": {}}
            ragas_scores = {
                "faithfulness": 0.0,
                "relevancy": 0.0,
                "retrieval": {"hit_rate": 0.0, "mrr": 0.0},
            }
            judge_result = {
                "final_score": 1.0,
                "agreement_rate": 0.0,
                "individual_scores": {},
                "error": str(exc),
            }
            status = "fail"

        return {
            "test_case": test_case.get("question", ""),
            "expected_answer": test_case.get("expected_answer", ""),
            "expected_retrieval_ids": test_case.get("expected_retrieval_ids", []),
            "agent_response": response.get("answer", ""),
            "retrieved_ids": response.get("retrieved_ids", []),
            "latency": round(latency, 4),
            "ragas": ragas_scores,
            "judge": judge_result,
            "metadata": {
                "case_type": test_case.get("metadata", {}).get("type", "unknown"),
                "difficulty": test_case.get("metadata", {}).get("difficulty", "unknown"),
                "agent": response.get("metadata", {}),
            },
            "status": status,
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
