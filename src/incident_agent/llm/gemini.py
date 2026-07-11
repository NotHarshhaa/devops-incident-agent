"""Google Gemini provider (lazily imports ``google-generativeai``)."""

from __future__ import annotations

from .base import LLMProvider


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash") -> None:
        super().__init__(model)
        self.api_key = api_key
        self._model = None  # lazily constructed client

    def _client(self):
        if self._model is None:
            import google.generativeai as genai  # lazy import

            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(self.model)
        return self._model

    def complete(self, system: str, user: str) -> str:
        model = self._client()
        # Gemini has no dedicated system role; prepend it to the prompt.
        prompt = f"{system}\n\n{user}"
        response = model.generate_content(prompt)
        return (response.text or "").strip()
