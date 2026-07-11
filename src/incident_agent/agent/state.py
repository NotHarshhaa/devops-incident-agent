"""Shared state passed between agent steps.

Modeled as a plain ``TypedDict`` so it works both with LangGraph (when
installed) and the built-in pure-Python orchestrator.
"""

from __future__ import annotations

from typing import TypedDict

from ..models import Evidence, Incident, RootCause


class AgentState(TypedDict, total=False):
    incident: Incident
    plan: list[str]
    evidence: list[Evidence]
    root_cause: RootCause
    timeline: list[str]
    provider: str
