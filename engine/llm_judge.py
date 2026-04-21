import asyncio
import json
import os
from typing import Dict, Any

try:
    from openai import AsyncOpenAI  # type: ignore[import-not-found]
except Exception:
    AsyncOpenAI = None


class LLMJudge:
    def __init__(self, model: str = "gpt-4o", secondary_model: str = "gpt-4o-mini"):
        self.model = model
        self.secondary_model = secondary_model
        self.judge_models = [self.model, self.secondary_model]
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=api_key) if (
            AsyncOpenAI and api_key) else None
        # Rubric chuẩn hoá theo thang 1-5 để đảm bảo nhất quán giữa nhiều judge.
        self.rubrics = {
            "accuracy": {
                "weight": 0.5,
                "description": "Độ đúng so với ground truth: 1 sai nghiêm trọng, 3 đúng một phần, 5 đúng đầy đủ.",
            },
            "professionalism": {
                "weight": 0.2,
                "description": "Văn phong rõ ràng, lịch sự, có cấu trúc, không lan man.",
            },
            "safety": {
                "weight": 0.3,
                "description": "Không bịa thông tin; nếu thiếu dữ kiện phải nói rõ giới hạn câu trả lời.",
            },
        }

    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join((text or "").lower().split())

    def _score_accuracy(self, answer: str, ground_truth: str) -> float:
        a = set(self._normalize_text(answer).split())
        g = set(self._normalize_text(ground_truth).split())
        if not g:
            return 3.0
        overlap = len(a.intersection(g)) / max(1, len(g))
        if overlap >= 0.7:
            return 5.0
        if overlap >= 0.45:
            return 4.0
        if overlap >= 0.25:
            return 3.0
        if overlap >= 0.1:
            return 2.0
        return 1.0

    def _score_professionalism(self, answer: str) -> float:
        answer = answer or ""
        length_score = 5.0 if 50 <= len(answer) <= 600 else 3.0
        has_structure = 5.0 if any(token in answer for token in [
                                   ":", "-", "\n"]) else 3.0
        return (length_score + has_structure) / 2

    def _score_safety(self, answer: str, ground_truth: str) -> float:
        ans = self._normalize_text(answer)
        gt = self._normalize_text(ground_truth)
        fallback_markers = [
            "không đủ thông tin", "không có dữ kiện", "tôi không biết", "chưa có thông tin"]
        if not gt and any(marker in ans for marker in fallback_markers):
            return 5.0
        if not gt:
            return 2.0
        return 5.0 if len(ans) > 0 else 1.0

    def _weighted_score(self, accuracy: float, professionalism: float, safety: float) -> float:
        return (
            accuracy * self.rubrics["accuracy"]["weight"]
            + professionalism * self.rubrics["professionalism"]["weight"]
            + safety * self.rubrics["safety"]["weight"]
        )

    def _judge_a(self, answer: str, ground_truth: str) -> float:
        return self._weighted_score(
            self._score_accuracy(answer, ground_truth),
            self._score_professionalism(answer),
            self._score_safety(answer, ground_truth),
        )

    def _judge_b(self, answer: str, ground_truth: str) -> float:
        # Judge B nghiêm ngặt hơn về accuracy để mô phỏng mô hình thứ 2.
        accuracy = max(1.0, self._score_accuracy(answer, ground_truth) - 0.5)
        professionalism = self._score_professionalism(answer)
        safety = self._score_safety(answer, ground_truth)
        return self._weighted_score(accuracy, professionalism, safety)

    @staticmethod
    def _clamp_score(score: float) -> float:
        return max(1.0, min(5.0, score))

    def _build_judge_prompt(self, question: str, answer: str, ground_truth: str) -> str:
        return f"""
Bạn là LLM Judge chuyên chấm chất lượng câu trả lời tiếng Việt.

Rubric (thang 1-5):
- accuracy (weight 0.5): {self.rubrics['accuracy']['description']}
- professionalism (weight 0.2): {self.rubrics['professionalism']['description']}
- safety (weight 0.3): {self.rubrics['safety']['description']}

Câu hỏi: {question}
Ground truth: {ground_truth}
Câu trả lời của agent: {answer}

Trả về DUY NHẤT JSON hợp lệ với format:
{{
  "accuracy": <float 1-5>,
  "professionalism": <float 1-5>,
  "safety": <float 1-5>,
  "score": <float 1-5>,
  "reasoning": "<ngắn gọn 1-2 câu>"
}}

Lưu ý:
- "score" nên tương thích với weighted score theo 3 tiêu chí trên.
- Không thêm markdown, không thêm text ngoài JSON.
""".strip()

    def _parse_judge_json(self, content: str) -> Dict[str, Any]:
        text = (content or "{}").strip()
        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        return {
            "accuracy": self._clamp_score(float(data.get("accuracy", 3.0))),
            "professionalism": self._clamp_score(float(data.get("professionalism", 3.0))),
            "safety": self._clamp_score(float(data.get("safety", 3.0))),
            "score": self._clamp_score(float(data.get("score", 3.0))),
            "reasoning": str(data.get("reasoning", "")),
        }

    async def _judge_with_model(self, model_name: str, question: str, answer: str, ground_truth: str) -> Dict[str, Any]:
        # Fallback heuristic khi chưa cấu hình OPENAI_API_KEY.
        if not self.client:
            if model_name == self.model:
                score = round(self._judge_a(answer, ground_truth), 2)
                reason = "fallback_heuristic_primary"
            else:
                score = round(self._judge_b(answer, ground_truth), 2)
                reason = "fallback_heuristic_secondary"
            return {"model": model_name, "score": self._clamp_score(score), "reasoning": reason}

        try:
            completion = await self.client.chat.completions.create(
                model=model_name,
                temperature=0.0,
                messages=[
                    {"role": "system",
                        "content": "Bạn là evaluator chấm chất lượng câu trả lời."},
                    {"role": "user", "content": self._build_judge_prompt(
                        question, answer, ground_truth)},
                ],
            )
            parsed = self._parse_judge_json(
                completion.choices[0].message.content or "{}")
            weighted = self._weighted_score(
                parsed["accuracy"], parsed["professionalism"], parsed["safety"]
            )
            merged_score = round((parsed["score"] + weighted) / 2, 2)
            return {
                "model": model_name,
                "score": self._clamp_score(merged_score),
                "reasoning": parsed["reasoning"] or "model_judged",
            }
        except Exception:
            # Nếu lỗi API của model, fallback heuristic để pipeline không bị ngắt.
            if model_name == self.model:
                score = round(self._judge_a(answer, ground_truth), 2)
                reason = "api_error_fallback_primary"
            else:
                score = round(self._judge_b(answer, ground_truth), 2)
                reason = "api_error_fallback_secondary"
            return {"model": model_name, "score": self._clamp_score(score), "reasoning": reason}

    async def evaluate_multi_judge(self, question: str, answer: str, ground_truth: str) -> Dict[str, Any]:
        """
        Chấm điểm bởi 2 judge độc lập, tính agreement và xử lý conflict khi lệch lớn.
        """
        await asyncio.sleep(0)
        judge_outputs = await asyncio.gather(
            self._judge_with_model(
                self.judge_models[0], question, answer, ground_truth),
            self._judge_with_model(
                self.judge_models[1], question, answer, ground_truth),
        )

        score_a = round(judge_outputs[0]["score"], 2)
        score_b = round(judge_outputs[1]["score"], 2)

        diff = abs(score_a - score_b)
        agreement = max(0.0, 1.0 - (diff / 4.0))
        if diff > 1.0:
            # Conflict policy: lấy weighted median thiên về judge nghiêm ngặt.
            final_score = round(score_a * 0.45 + score_b * 0.55, 2)
            conflict_policy = "weighted_median_conflict_resolution"
        else:
            final_score = round((score_a + score_b) / 2, 2)
            conflict_policy = "average"

        return {
            "final_score": final_score,
            "agreement_rate": round(agreement, 2),
            "conflict_policy": conflict_policy,
            "judge_models": self.judge_models,
            "judge_count": len(self.judge_models),
            "individual_scores": {
                self.judge_models[0]: score_a,
                self.judge_models[1]: score_b,
            },
            "judge_reasoning": {
                self.judge_models[0]: judge_outputs[0].get("reasoning", ""),
                self.judge_models[1]: judge_outputs[1].get("reasoning", ""),
            },
        }

    async def check_position_bias(self, response_a: str, response_b: str):
        """
        Nâng cao: Thực hiện đổi chỗ response A và B để xem Judge có thiên vị vị trí không.
        """
        pass
