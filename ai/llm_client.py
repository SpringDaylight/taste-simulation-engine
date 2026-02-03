import os
import json
import time
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

load_dotenv()


class BedrockClient:
    def __init__(self):
        self.region = os.getenv("AWS_REGION", "ap-northeast-2")
        self.model_id = os.getenv("BEDROCK_MODEL_ID")
        self.max_tokens = int(os.getenv("BEDROCK_MAX_TOKENS", "1024"))
        self.temperature = float(os.getenv("BEDROCK_TEMPERATURE", "0.2"))

        if not self.model_id:
            raise ValueError("BEDROCK_MODEL_ID is not set")

        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=self.region
        )

    def invoke(self, system_prompt: str, user_prompt: str, retry: int = 2) -> str:
        """
        Bedrock LLM 호출 (Claude 계열 기준)
        반환값: raw text (string)
        """

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        }

        for attempt in range(retry + 1):
            try:
                response = self.client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(body),
                    accept="application/json",
                    contentType="application/json",
                )

                response_body = json.loads(response["body"].read())
                return response_body["content"][0]["text"]

            except (BotoCoreError, ClientError, KeyError) as e:
                if attempt >= retry:
                    raise RuntimeError(f"Bedrock invoke failed: {e}")
                time.sleep(1.5 * (attempt + 1))
