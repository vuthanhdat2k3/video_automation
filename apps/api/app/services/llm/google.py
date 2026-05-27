import httpx
from pydantic import BaseModel

from .base import LLMProvider, extract_json_block


class GoogleProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash-lite",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        max_tokens: int = 8192,
        temperature: float = 0.7,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def generate(
        self, system_prompt: str, user_prompt: str, response_schema: type[BaseModel]
    ) -> dict:
        return await self.generate_with_retry(system_prompt, user_prompt, response_schema)

    async def chat(self, messages: list[dict]) -> str:
        contents = []
        system_instruction = None

        for msg in messages:
            role = msg.get("role", "user")
            text = msg.get("content", "")
            if role == "system":
                system_instruction = text
            else:
                gemini_role = "model" if role == "assistant" else "user"
                contents.append({"role": gemini_role, "parts": [{"text": text}]})

        body = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": self.max_tokens,
                "temperature": self.temperature,
            },
        }
        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                f"{self.base_url}/models/{self.model}:generateContent",
                json=body,
                headers=headers,
            )
            if resp.status_code == 429:
                raise RuntimeError("Google API rate limited (429)")
            resp.raise_for_status()
            data = resp.json()

            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError(f"Google API returned no candidates: {data}")
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
            return text
