import httpx
from pydantic import BaseModel

from .base import LLMProvider, extract_json_block


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:14b", max_tokens: int = 4096):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens

    async def generate(
        self, system_prompt: str, user_prompt: str, response_schema: type[BaseModel]
    ) -> dict:
        return await self.generate_with_retry(system_prompt, user_prompt, response_schema)

    async def chat(self, messages: list[dict]) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "format": "json",
                    "options": {
                        "num_predict": self.max_tokens,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]
