from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="/home/dat/pipeline/video_automation/.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://ai2d:ai2d_pass@localhost:15432/ai2d_flow"
    redis_url: str = "redis://localhost:6379/0"
    storage_root: str = "./storage"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    log_level: str = "INFO"
    llm_provider: str = "ollama"
    llm_model: str = "qwen2.5:14b"
    llm_base_url: str = "http://localhost:11434"
    llm_api_key: str | None = None
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.7

    # ComfyUI
    comfyui_base_url: str = "http://localhost:8188"
    comfyui_timeout: int = 300
    comfyui_default_checkpoint: str = "animagine-xl-4.0-opt.safetensors"

    @model_validator(mode="after")
    def resolve_paths(self) -> "Settings":
        p = Path(self.storage_root)
        if not p.is_absolute():
            self.storage_root = str(PROJECT_ROOT / p)
        return self


settings = Settings()
