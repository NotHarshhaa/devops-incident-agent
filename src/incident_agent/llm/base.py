"""LLM provider abstraction.

Every provider implements :meth:`complete`. The shared :meth:`analyze`
turns an incident + evidence into a :class:`RootCause` using the common
prompt/parse contract, with a rule-based fallback so a malformed model
response never crashes an investigation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Evidence, Incident, RootCause
from .heuristics import heuristic_root_cause
from .prompts import SYSTEM_PROMPT, build_user_prompt, parse_root_cause


class LLMProvider(ABC):
    """Common interface for all LLM backends."""

    #: short provider identifier, e.g. "gemini"
    name: str = "base"

    def __init__(self, model: str) -> None:
        self.model = model

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Return the model's raw text completion for the given prompts."""
        raise NotImplementedError

    def analyze(self, incident: Incident, evidence: list[Evidence]) -> RootCause:
        """Produce a root-cause analysis for an incident."""
        user = build_user_prompt(incident, evidence)
        try:
            raw = self.complete(SYSTEM_PROMPT, user)
            root = parse_root_cause(raw)
            if root.summary and root.summary != "Undetermined root cause":
                return root
        except Exception:  # noqa: BLE001 - never let the LLM break the flow
            pass
        # Fallback: explainable rule-based reasoning.
        return heuristic_root_cause(incident, evidence)


class MockProvider(LLMProvider):
    """Offline, deterministic provider backed by the rule-based engine.

    Requires no API key or network access — used for demos, CI and as the
    global fallback when ``MOCK_MODE`` is enabled.
    """

    name = "mock"

    def __init__(self, model: str = "rule-based-v1") -> None:
        super().__init__(model)

    def complete(self, system: str, user: str) -> str:  # pragma: no cover
        # Not used directly; analyze() is overridden below.
        return "{}"

    def analyze(self, incident: Incident, evidence: list[Evidence]) -> RootCause:
        return heuristic_root_cause(incident, evidence)
