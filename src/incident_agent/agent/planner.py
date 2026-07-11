"""Incident planner.

Produces the ordered investigation plan — which evidence sources to consult
for a given incident. Kept deliberately simple and explainable; it can later
be upgraded to an LLM-driven planner without changing callers.
"""

from __future__ import annotations

from ..collectors import build_collectors
from ..config import Settings, get_settings
from ..models import Incident


def make_plan(incident: Incident, settings: Settings | None = None) -> list[str]:
    settings = settings or get_settings()
    collectors = build_collectors(settings)
    steps = ["Received alert: " + incident.title]
    for c in collectors:
        mode = "mock" if (settings.mock_mode or not c.available()) else "live"
        steps.append(f"Collect evidence from {c.name} ({mode})")
    steps.append("Correlate evidence and determine probable root cause")
    steps.append("Produce incident report and await human approval")
    return steps
