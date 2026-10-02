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
    # With an Anthropic key the lead investigator and every specialist are
    # model-driven: they choose tools, read the results and decide whether to
    # dig further. Without one the same agents run on rule policies that are
    # also observation-driven; only the reasoning is by rule.
    llm_provider: str = "anthropic"
    llm_api_key: str = ""
    llm_model: str = "claude-opus-5-5"
    llm_base_url: str = ""
    llm_timeout_seconds: int = 60
    llm_fallbacks: bool = True          # server-side refusal fallback (Claude API only)
    llm_lead_effort: str = "medium"     # lead investigator: plans, re-plans, concludes
    llm_agent_effort: str = "low"       # specialists: narrow tool loops

    # --- agent budgets ----------------------------------------------------
    # The deployment's function limit is 60s; the deadline leaves room to
    # conclude and persist after the last delegation returns.
    agent_deadline_seconds: int = 40
    agent_max_turns: int = 5            # model turns per specialist
    lead_max_turns: int = 4             # model turns for the lead investigator
    lead_max_delegations: int = 8

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
