import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "DRMS"
    DEBUG: str = "TRUE"
    LOCAL_TIMEZONE: str = "Africa/Algiers"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "*"

    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5
    DATABASE_POOL_TTL: int = 60 * 20
    DATABASE_POOL_PRE_PING: bool = True

    FIRST_SUPERUSER_USERNAME: str = "superuser"
    FIRST_SUPERUSER_PASSWORD: str = "superuser123"

    UPLOAD_DIR: str = "uploads/documents"

    # Secret key for encrypting share links (32 url-safe base64-encoded bytes)
    SHARE_LINK_SECRET_KEY: str = "uifncAbVYX19EKKpF6HBUAmDerMY52r4ggx0gXAujrM="

    # Telegram bot token from @BotFather
    TELEGRAM_BOT_TOKEN: str = ""

    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3:8b"
    OLLAMA_MAX_ITERATIONS: int = 3
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    REDIS_URL: str = "redis://localhost:6379"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    QDRANT_URL: str = "http://localhost:6333"

    if os.environ.get("ENV_FILE") == ".env.test":
        model_config = SettingsConfigDict(
            env_file=".env.test", env_file_encoding="utf-8"
        )
    else:
        model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins_list(self) -> list[str]:
        raw = self.CORS_ORIGINS.strip()
        if not raw:
            return []
        return [p.strip() for p in raw.split(",") if p.strip()]

    @property
    def is_debug(self) -> bool:
        return self.DEBUG.lower() == "true"


settings = Settings()  # type: ignore
