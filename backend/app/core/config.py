from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Anchor the .env lookup to the backend package rather than the process working
# directory. A relative "env_file" is resolved against the CWD, so launching the
# app from anywhere other than backend/ silently skipped the file and fell back
# to the localhost default. Real environment variables still take precedence,
# which is how configuration is supplied in deployment (no .env file present).
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = "postgresql://postgres:postgres@localhost:5432/retailiq"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_title: str = "RetailIQ API"
    api_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    debug: bool = False

    # --- security -------------------------------------------------------
    # Overridden in deployment. A generated fallback keeps local dev working
    # but invalidates tokens on restart, which is the safe failure mode.
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 12
    cors_origins: str = "*"

    # --- LLM (optional) --------------------------------------------------
    # When llm_api_key is set the copilot uses the provider for planning and
    # narrative synthesis. Without it the agent pipeline still runs end to end
    # using its deterministic planner; only the prose is templated.
    llm_provider: str = "anthropic"
    llm_api_key: str = ""
    llm_model: str = "claude-sonnet-5"
    llm_base_url: str = ""
    llm_timeout_seconds: int = 60

    # --- analytics cache -------------------------------------------------
    analytics_cache_seconds: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
