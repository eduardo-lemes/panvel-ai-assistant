from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[4] / ".env")

_ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    environment: str
    debug: bool
    log_level: str
    llm_provider: str
    llm_model: str
    openai_api_key: str | None
    embedding_provider: str
    vector_store_path: Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache
def get_settings() -> Settings:
    llm_provider = os.getenv("LLM_PROVIDER", "mock")
    return Settings(
        app_name=os.getenv("APP_NAME", "Panvel AI Assistant API"),
        app_version=os.getenv("APP_VERSION", "0.1.0"),
        environment=os.getenv("APP_ENV", "local"),
        debug=_as_bool(os.getenv("APP_DEBUG"), default=False),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        llm_provider=llm_provider,
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", llm_provider),
        vector_store_path=Path(os.getenv("VECTOR_STORE_PATH", str(_ROOT / "backend" / ".vector_store"))),
    )
