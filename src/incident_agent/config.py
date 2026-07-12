"""Application configuration.

All settings are read from environment variables (and an optional ``.env``
file). Every integration is optional — with no configuration the agent runs
fully in *mock mode* using synthetic evidence, so it works out of the box.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProviderName = Literal["gemini", "openai", "anthropic", "mock"]

# Sensible default models per provider, used when LLM_MODEL is not set.
DEFAULT_MODELS: dict[str, str] = {
    "gemini": "gemini-1.5-flash",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-latest",
    "mock": "rule-based-v1",
}


class Settings(BaseSettings):
    """Typed application settings loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- App ----
    app_name: str = "DevOps Incident Agent"
    app_env: Literal["development", "production"] = "development"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    # ---- LLM ----
    llm_provider: LLMProviderName = "gemini"
    llm_model: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # ---- Global mock switch ----
    mock_mode: bool = True

    # ---- Prometheus ----
    prometheus_url: Optional[str] = None

    # ---- Loki ----
    loki_url: Optional[str] = None

    # ---- Kubernetes ----
    kubeconfig: Optional[str] = None
    k8s_namespace: str = "default"

    # ---- GitHub ----
    github_token: Optional[str] = None
    github_repo: Optional[str] = None

    # ---- Jenkins ----
    jenkins_url: Optional[str] = None
    jenkins_user: Optional[str] = None
    jenkins_token: Optional[str] = None

    # ---- Storage ----
    database_url: Optional[str] = None
    redis_url: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Derived helpers
    # ------------------------------------------------------------------ #
    def api_key_for(self, provider: str) -> Optional[str]:
        return {
            "gemini": self.gemini_api_key,
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
        }.get(provider)

    def resolved_model(self, provider: str) -> str:
        return self.llm_model or DEFAULT_MODELS.get(provider, "rule-based-v1")

    def effective_provider(self) -> str:
        """Return the provider that will actually be used.

        Falls back to ``mock`` when global mock mode is on, or when the
        configured provider has no API key available.
        """
        if self.mock_mode:
            return "mock"
        if self.llm_provider == "mock":
            return "mock"
        if not self.api_key_for(self.llm_provider):
            return "mock"
        return self.llm_provider


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
