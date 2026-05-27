from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
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

    # --- LLM provider selector ---
    llm_provider: str = "ollama"

    # --- OpenAI-compatible (OpenAI, vLLM, TGI, etc.) ---
    openai_base_url: str = ""
    openai_api_key: str = ""
    openai_model: str = ""
    openai_max_tokens: int = 8192
    openai_temperature: float = 0.7

    # --- OpenRouter (for free/lightweight translation and DNA extraction) ---
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    # --- Generic LLM base URL/key (used by TTS, translation, etc.) ---
    llm_base_url: str = ""
    llm_api_key: str = ""

    # --- Google Gemini ---
    google_api_key: str = ""
    google_model: str = ""
    google_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    google_max_tokens: int = 8192
    google_temperature: float = 0.7

    # --- Ollama ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = ""
    ollama_max_tokens: int = 4096

    # ComfyUI
    comfyui_base_url: str = "http://localhost:8188"
    comfyui_timeout: int = 300
    comfyui_default_checkpoint: str = "animagine-xl-4.0-opt.safetensors"
    comfyui_input_dir: str = ""
    wan2_comfyui_base_url: str = ""

    # --- S3/Supabase Storage ---
    use_s3_storage: bool = False
    s3_endpoint_url: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_bucket_name: str = "root"
    s3_region_name: str = "ap-southeast-2"

    @model_validator(mode="after")
    def resolve_paths(self) -> "Settings":
        p = Path(self.storage_root)
        if not p.is_absolute():
            self.storage_root = str(PROJECT_ROOT / p)
        if not self.comfyui_input_dir:
            self.comfyui_input_dir = str(Path.home() / "pipeline" / "ComfyUI" / "input")
            
        # Automatically rewrite postgresql:// to postgresql+asyncpg:// for async pg engine
        if self.database_url.startswith("postgresql://"):
            self.database_url = "postgresql+asyncpg://" + self.database_url[len("postgresql://"):]
            
        return self


settings = Settings()
