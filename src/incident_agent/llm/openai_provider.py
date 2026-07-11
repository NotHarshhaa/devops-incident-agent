"""OpenAI provider (lazily imports ``openai``)."""

from __future__ import annotations

from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        super().__init__(model)
        self.api_key = api_key
        self._client_obj = None

    def _client(self):
        if self._client_obj is None:
            from openai import OpenAI  # lazy import

            self._client_obj = OpenAI(api_key=self.api_key)
        return self._client_obj

    def complete(self, system: str, user: str) -> str:
        client = self._client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.1,
        )
        return (response.choices[0].message.content or "").strip()
