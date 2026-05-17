import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = os.environ.get("DATABASE_URL", "")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/2")
    openai_api_key: str = os.environ.get("OPENAI_API_KEY", "")
    ai_engine_port: int = int(os.getenv("AI_ENGINE_PORT", "8002"))
    log_level: str = os.getenv("LOG_LEVEL", "info")

    # AI sozlamalari
    ai_model_primary: str = "gpt-4o-mini"
    ai_model_fallback: str = "gpt-4o"
    ai_batch_size: int = 15
    ai_max_retries: int = 3

    # Fayl cheklovlari
    max_file_size_mb: int = 10
    default_set_size: int = 20

    class Config:
        env_file = ".env"


settings = Settings()
