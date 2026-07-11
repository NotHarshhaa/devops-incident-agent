"""LLM provider factory.

Chooses a provider based on :class:`Settings`. Always degrades safely to the
offline :class:`MockProvider` when mock mode is on or no API key is present,
so the agent is never hard-blocked on external credentials.
"""

from __future__ import annotations

from ..config import Settings, get_settings
from .base import LLMProvider, MockProvider


def build_llm(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    provider = settings.effective_provider()

    if provider == "mock":
        return MockProvider(model=settings.resolved_model("mock"))

    api_key = settings.api_key_for(provider)
    model = settings.resolved_model(provider)

    if provider == "gemini":
        from .gemini import GeminiProvider

        return GeminiProvider(api_key=api_key, model=model)
    if provider == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(api_key=api_key, model=model)
    if provider == "anthropic":
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider(api_key=api_key, model=model)

    # Unknown provider name -> safe fallback.
    return MockProvider(model=settings.resolved_model("mock"))


__all__ = ["LLMProvider", "MockProvider", "build_llm"]
