from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://ai2d:ai2d_pass@localhost:5432/ai2d_flow"
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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
