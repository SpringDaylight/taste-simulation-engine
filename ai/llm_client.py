import json
import re


class LLMClient:
    def invoke(self, prompt_text: str) -> str:
        raise NotImplementedError


class MockLLMClient(LLMClient):
    def invoke(self, prompt_text: str) -> str:
        # Very small heuristic for local tests without a real LLM.
        text_match = re.search(r"다음 텍스트를 분석해라:\s*(.*)", prompt_text, re.DOTALL)
        input_text = text_match.group(1).strip() if text_match else ""
        result = {
            "emotion_tone": [],
            "narrative_focus": [],
            "pacing": "medium",
            "ending_preference": "open",
        }

        if "잔잔" in input_text or "여운" in input_text:
            result["emotion_tone"] = ["calm", "melancholic"]
            result["pacing"] = "slow"
        if "긴장" in input_text or "스릴" in input_text:
            result["emotion_tone"] = ["tense"]
            result["pacing"] = "fast"
        if "결말" in input_text or "시원" in input_text:
            result["ending_preference"] = "clear"

        return json.dumps(result, ensure_ascii=False)
