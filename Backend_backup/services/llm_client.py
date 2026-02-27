# LLM 추상 인터페이스 → Bedrock 호출(예상)
class LLMClient:
    def generate(self, prompt: str) -> str:
        pass
