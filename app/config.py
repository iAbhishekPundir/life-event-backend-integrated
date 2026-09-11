"""
Central application configuration.

Reads from environment variables (.env). Deliberately supports BOTH the
original GEMMA_* variable names the team already uses and a neutral LLM_*
set, so nothing breaks for anyone still running the old .env while the
naming is standardised.
"""
import os

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=False)


def _first_set(*names: str, default: str = "") -> str:
    """
    Returns the first of `names` that is actually present in the
    environment, even if set to an empty string -- an explicit `KEY=`
    in .env means "disabled", not "fall through to default". Only
    when none of `names` were set at all does `default` apply.
    """
    for name in names:
        if name in os.environ:
            return os.environ[name]
    return default


class Settings:
    # --- Database ---
    database_url: str = os.getenv("DATABASE_URL", "")

    # --- CORS ---
    allowed_origins: str = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
    )

    # --- LLM (provider-agnostic, OpenAI-compatible chat completions) ---
    # LLM_* takes precedence; GEMMA_* kept for backwards compatibility.
    llm_api_key: str = _first_set("LLM_API_KEY", "GEMMA_API_KEY")
    llm_api_url: str = _first_set(
        "LLM_API_URL",
        "GEMMA_API_URL",
        default="http://localhost:11434/v1/chat/completions",
    )
    llm_model_name: str = _first_set(
        "LLM_MODEL_NAME",
        "GEMMA_MODEL_NAME",
        default="gemma2",
    )
    llm_timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS") or "30")

    @property
    def allowed_origins_list(self) -> list:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def llm_configured(self) -> bool:
        """
        A local provider (Ollama / vLLM / LM Studio) needs no API key, so a
        configured URL is enough. A hosted provider needs a key as well.
        """
        url = (self.llm_api_url or "").lower()
        is_local = "localhost" in url or "127.0.0.1" in url or "0.0.0.0" in url
        return bool(url) and (is_local or bool(self.llm_api_key))


settings = Settings()
