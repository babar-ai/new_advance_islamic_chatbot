
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    VERSION: str = "1.3"
    LOGGING_DIR: str = "logs"
    LLM_MODEL: str = "gpt-4.1-nano"
    # LLM_MODEL: str = "gpt-4o"

    # Embedding Model Settings
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    # Qdrant Connection Settings
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""

    # Qdrant Vector Collection Names
    QURAN_COLLECTION_NAME: str = "quran"     
    HADITH_COLLECTION_NAME: str = "hadith"
    TAFSEER_COLLECTION_NAME: str = "tafsir"
    ISLAMIC_INFO_COLLECTION_NAME: str = "general_islamic_info"
    CLASSIFICATION_CACHE_COLLECTION_NAME: str = "classification_cache"

    # Redis Connection & Caching Settings (Layer 1)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_TTL: int = 2592000  # 30 days in seconds (0 for no expiration)

    # Ingestion & Chunking Parameters
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 150
    BATCH_SIZE: int = 500
    FORCE_RECREATE: bool = True

    # API Keys (defaults to empty string if not present in environment or .env)
    TAVILY_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # ── LangSmith Observability ───────────────────────────────────────────────
    LANGCHAIN_TRACING_V2: str = "false"
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "islamic-chatbot"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def COLLECTION_NAMES(self) -> dict[str, str]:
        return {
            "quran": self.QURAN_COLLECTION_NAME,
            "hadith": self.HADITH_COLLECTION_NAME,
            "tafseer": self.TAFSEER_COLLECTION_NAME,
            "general_islamic_info": self.ISLAMIC_INFO_COLLECTION_NAME,
        }

    @property
    def langsmith_enabled(self) -> bool:
        """Returns True if LangSmith tracing is configured and enabled."""
        return (
            self.LANGCHAIN_TRACING_V2.lower() == "true"
            and bool(self.LANGCHAIN_API_KEY)
            and self.LANGCHAIN_API_KEY != ""
        )


settings = Settings()

