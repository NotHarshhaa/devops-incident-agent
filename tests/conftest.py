"""Shared pytest fixtures.

Every test runs in forced MOCK_MODE so the suite is fully offline and
deterministic — no API keys, no Prometheus, no Kubernetes required.
"""

from __future__ import annotations

import pytest

from incident_agent.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _force_mock_env(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "true")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    # Clear caches so settings pick up the patched env.
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def settings() -> Settings:
    return Settings(mock_mode=True, llm_provider="mock")


@pytest.fixture
def sample_incident():
    from incident_agent.models import Incident, Severity

    return Incident(
        title="Production API latency increased to 8 seconds",
        description="Users report slow responses on the checkout API.",
        severity=Severity.CRITICAL,
        service="api",
        namespace="production",
    )
