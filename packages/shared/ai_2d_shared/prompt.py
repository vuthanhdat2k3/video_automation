from uuid import UUID

from pydantic import BaseModel, Field


class PromptPackage(BaseModel):
    """Compiled prompt strings ready for each engine in the pipeline."""
    project_id: UUID
    t2i_prompt: str | None = None  # ComfyUI text-to-image prompt
    i2v_prompt: str | None = None  # ComfyUI image-to-video / AnimateDiff prompt
    tts_prompt: str | None = None  # edge-tts input text
    llm_prompt: str | None = None  # LLM context for story / reasoning
    metadata: dict = Field(default_factory=dict)
