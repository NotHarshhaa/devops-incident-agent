"""Reasoning / root-cause engine.

Thin wrapper that hands the incident + evidence to the configured LLM
provider (which itself falls back to the rule-based engine when needed).
"""

from __future__ import annotations

from ..config import Settings, get_settings
from ..llm import LLMProvider, build_llm
from ..models import Evidence, Incident, RootCause


def reason_root_cause(
    incident: Incident,
    evidence: list[Evidence],
    llm: LLMProvider | None = None,
    settings: Settings | None = None,
) -> RootCause:
    settings = settings or get_settings()
    llm = llm or build_llm(settings)
    return llm.analyze(incident, evidence)
