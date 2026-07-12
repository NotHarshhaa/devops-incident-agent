"""Prompt construction and response parsing for the reasoning step.

Kept separate from providers so every backend (Gemini/OpenAI/Anthropic)
shares the exact same prompt and JSON contract.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..models import Evidence, Incident, RemediationType, RootCause

SYSTEM_PROMPT = (
    "You are a senior Site Reliability Engineer acting as an incident "
    "investigator. You are given an incident and a list of evidence gathered "
    "from metrics, logs, Kubernetes, deployments and CI/CD systems. "
    "Analyze the evidence and determine the single most probable root cause. "
    "Be concise, technical and decisive. You never execute changes yourself; "
    "you only recommend an action for a human to approve.\n\n"
    "Respond with ONLY a JSON object (no markdown fences) of the form:\n"
    "{\n"
    '  "summary": "one-sentence probable root cause",\n'
    '  "confidence": 0.0-1.0,\n'
    '  "contributing_factors": ["factor 1", "factor 2"],\n'
    '  "recommended_action": '
    '"rollback|scale|restart|config_change|investigate|none",\n'
    '  "recommendation_detail": "what the human should do",\n'
    '  "risk": "risk of the recommended action"\n'
    "}"
)


def build_user_prompt(incident: Incident, evidence: list[Evidence]) -> str:
    lines: list[str] = []
    lines.append("## INCIDENT")
    lines.append(f"Title: {incident.title}")
    lines.append(f"Severity: {incident.severity.value}")
    if incident.service:
        lines.append(f"Service: {incident.service}")
    if incident.namespace:
        lines.append(f"Namespace: {incident.namespace}")
    if incident.description:
        lines.append(f"Description: {incident.description}")

    lines.append("\n## EVIDENCE")
    if not evidence:
        lines.append("(no evidence collected)")
    for i, ev in enumerate(evidence, 1):
        flag = " [ANOMALY]" if ev.anomalous else ""
        lines.append(
            f"{i}. ({ev.source}/{ev.kind.value}){flag} {ev.summary}"
        )
        if ev.detail:
            lines.append(f"   detail: {ev.detail}")

    lines.append("\nReturn the JSON object described in the system prompt.")
    return "\n".join(lines)


def parse_root_cause(text: str) -> RootCause:
    """Parse an LLM response into a RootCause, tolerating minor noise."""
    data = _extract_json(text)

    action_raw = str(data.get("recommended_action", "investigate")).lower()
    try:
        action = RemediationType(action_raw)
    except ValueError:
        action = RemediationType.INVESTIGATE

    confidence = data.get("confidence", 0.0)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    factors = data.get("contributing_factors", [])
    if isinstance(factors, str):
        factors = [factors]

    return RootCause(
        summary=str(data.get("summary", "Undetermined root cause")).strip(),
        confidence=confidence,
        contributing_factors=[str(f) for f in factors],
        recommended_action=action,
        recommendation_detail=str(data.get("recommendation_detail", "")).strip(),
        risk=str(data.get("risk", "")).strip(),
    )


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()

    # Fast path: the whole response is already a clean JSON object.
    obj = _try_load(text)
    if obj is not None:
        return obj

    # Strip markdown code fences if present.
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        obj = _try_load(fence.group(1))
        if obj is not None:
            return obj

    # Fall back to scanning for the first balanced {...} object, so
    # surrounding prose or stray braces don't get swallowed by a greedy
    # match (e.g. "Note: {...}\n{<real json>}" or trailing commentary).
    for candidate in _iter_balanced_braces(text):
        obj = _try_load(candidate)
        if obj is not None:
            return obj

    return {}


def _try_load(candidate: str) -> dict[str, Any] | None:
    try:
        obj = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _iter_balanced_braces(text: str):
    """Yield each top-level ``{...}`` substring found in ``text``, in order."""
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start != -1:
                    yield text[start : i + 1]
                    start = -1
