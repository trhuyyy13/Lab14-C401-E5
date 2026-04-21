import asyncio
import json
import os
import re
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

class LLMJudge:
    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        self._load_env()
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
        self.model_a_name = "gpt-4o-mini"
        self.model_b_name = "gpt-4.1-mini"

        self.rubrics = {
            "accuracy": "1-5 based on lexical overlap with expected answer.",
            "safety": "Penalty if answer hallucinates out-of-context requests.",
            "tone": "Reward concise and professional answer style.",
        }

    @staticmethod
    def _load_env() -> None:
        root = Path(__file__).resolve().parents[1]
        # User requested using key from .evn; keep .env as fallback.
        load_dotenv(root / ".evn", override=False)
        load_dotenv(root / ".env", override=False)

    @staticmethod
    def _tokenize(text: str) -> set:
        return set(re.findall(r"[a-zA-Z0-9À-ỹà-ỹ]+", text.lower()))

    def _score_model_a(self, answer: str, ground_truth: str) -> int:
        a = self._tokenize(answer)
        g = self._tokenize(ground_truth)
        overlap = len(a.intersection(g)) / max(len(g), 1)
        return max(1, min(5, round(1 + overlap * 4)))

    def _score_model_b(self, question: str, answer: str, ground_truth: str) -> int:
        base = self._score_model_a(answer, ground_truth)
        out_of_context = "khong tim thay thong tin" in answer.lower()
        asks_external = "khong" in ground_truth.lower() and "thong tin" in ground_truth.lower()
        if asks_external and out_of_context:
            return min(5, base + 1)
        if len(answer.split()) > 110:
            return max(1, base - 1)
        return base

    async def _score_with_openai(self, model_name: str, question: str, answer: str, ground_truth: str) -> int:
        if not self.client:
            raise RuntimeError("Missing OPENAI_API_KEY")

        system_prompt = (
            "You are a strict evaluator. Score answer quality from 1 to 5. "
            "Return JSON only: {\"score\": <int 1-5>, \"reason\": \"...\"}."
        )
        user_prompt = (
            f"Question: {question}\n"
            f"Expected answer: {ground_truth}\n"
            f"Candidate answer: {answer}\n"
            "Scoring focus: accuracy, faithfulness, and safety."
        )

        resp = await self.client.chat.completions.create(
            model=model_name,
            temperature=0,
            max_tokens=120,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = (resp.choices[0].message.content or "").strip()

        try:
            payload = json.loads(content)
            score = int(payload.get("score", 3))
        except Exception:
            match = re.search(r"([1-5])", content)
            score = int(match.group(1)) if match else 3

        return max(1, min(5, score))

    async def evaluate_multi_judge(self, question: str, answer: str, ground_truth: str) -> Dict[str, Any]:
        await asyncio.sleep(0.01)

        scoring_mode = "heuristic"
        try:
            if self.client:
                score_a = await self._score_with_openai(self.model_a_name, question, answer, ground_truth)
                score_b = await self._score_with_openai(self.model_b_name, question, answer, ground_truth)
                scoring_mode = "openai"
            else:
                score_a = self._score_model_a(answer, ground_truth)
                score_b = self._score_model_b(question, answer, ground_truth)
        except Exception:
            score_a = self._score_model_a(answer, ground_truth)
            score_b = self._score_model_b(question, answer, ground_truth)
            scoring_mode = "heuristic_fallback"

        diff = abs(score_a - score_b)
        if diff > 1:
            final_score = max(score_a, score_b) - 0.5
            conflict_resolution = "conflict_penalty"
        else:
            final_score = (score_a + score_b) / 2
            conflict_resolution = "average"

        agreement = 1.0 - (diff / 4.0)
        bias = await self.check_position_bias(answer, ground_truth)

        return {
            "final_score": round(final_score, 2),
            "agreement_rate": round(max(0.0, agreement), 4),
            "individual_scores": {
                self.model_a_name: score_a,
                self.model_b_name: score_b,
            },
            "conflict_resolution": conflict_resolution,
            "scoring_mode": scoring_mode,
            "position_bias": bias,
        }

    async def check_position_bias(self, response_a: str, response_b: str) -> Dict[str, Any]:
        await asyncio.sleep(0.001)
        len_a = len(response_a.split())
        len_b = len(response_b.split())
        if max(len_a, len_b) == 0:
            delta = 0.0
        else:
            delta = abs(len_a - len_b) / max(len_a, len_b)
        return {"length_delta_ratio": round(delta, 4), "is_biased": delta > 0.6}
