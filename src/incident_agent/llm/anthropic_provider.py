"""Anthropic Claude provider (lazily imports ``anthropic``)."""

from __future__ import annotations

from .base import LLMProvider


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(
        self, api_key: str, model: str = "claude-3-5-sonnet-latest"
    ) -> None:
        super().__init__(model)
        self.api_key = api_key
        self._client_obj = None

    def _client(self):
        if self._client_obj is None:
            import anthropic  # lazy import

            self._client_obj = anthropic.Anthropic(api_key=self.api_key)
        return self._client_obj

    def complete(self, system: str, user: str) -> str:
        client = self._client()
        message = client.messages.create(
            model=self.model,
            max_tokens=1024,
            temperature=0.1,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        parts = [block.text for block in message.content if hasattr(block, "text")]
        return "".join(parts).strip()
