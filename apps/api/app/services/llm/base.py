from abc import ABC, abstractmethod

from pydantic import BaseModel, ValidationError


class LLMGenerationError(Exception):
    pass


def extract_json_block(text: str) -> str:
    """Extract JSON from markdown code block or raw text."""
    text = text.strip()
    if "```" in text:
        blocks = text.split("```")
        for i, block in enumerate(blocks):
            if i % 2 == 1:  # code block content
                content = block.strip()
                if content.startswith("json"):
                    content = content[4:].strip()
                return content
    return text


class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self, system_prompt: str, user_prompt: str, response_schema: type[BaseModel]
    ) -> dict:
        ...

    @abstractmethod
    async def chat(self, messages: list[dict]) -> str:
        ...

    async def generate_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        max_retries: int = 2,
    ) -> dict:
        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            current_prompt = user_prompt
            if attempt > 0 and last_error:
                current_prompt = (
                    user_prompt
                    + f"\n\nPrevious response was invalid: {last_error}. "
                    f"Please fix and return valid JSON matching this schema: "
                    f"{response_schema.model_json_schema()}"
                )
            response = await self.chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": current_prompt},
                ]
            )
            try:
                raw = extract_json_block(response)
                parsed = response_schema.model_validate_json(raw)
                return parsed.model_dump()
            except (ValidationError, ValueError) as e:
                last_error = e
                continue
        raise LLMGenerationError(
            f"Failed to generate valid {response_schema.__name__} "
            f"after {max_retries + 1} attempts. Last error: {last_error}"
        )
