"""Incident memory — surfaces similar past incidents from the report store.

Deliberately dependency-free and explainable (no embeddings/vector DB): it
scores past reports against the current incident using simple, inspectable
signals — title word overlap, same service, same severity — consistent with
the project's "explainability over black-box" design principle.
"""

from __future__ import annotations

import re

from ..models import Incident, Report, SimilarIncident
from ..store import ReportStore

#: Common words that don't carry incident-specific signal.
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "to", "of", "in", "on",
    "for", "and", "or", "with", "at", "by", "has", "have", "had",
}

#: Weights for each similarity signal; must sum to 1.0.
_TITLE_WEIGHT = 0.6
_SERVICE_WEIGHT = 0.25
_SEVERITY_WEIGHT = 0.15


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 1}


def _title_similarity(a: str, b: str) -> float:
    tokens_a, tokens_b = _tokenize(a), _tokenize(b)
    if not tokens_a or not tokens_b:
        return 0.0
    overlap = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(overlap) / len(union) if union else 0.0


def score_similarity(incident: Incident, past: Report) -> float:
    """Return a 0.0-1.0 similarity score between ``incident`` and a past report."""
    score = _TITLE_WEIGHT * _title_similarity(incident.title, past.incident.title)

    if incident.service and past.incident.service:
        score += _SERVICE_WEIGHT * (1.0 if incident.service == past.incident.service else 0.0)

    if incident.severity == past.incident.severity:
        score += _SEVERITY_WEIGHT

    return round(min(score, 1.0), 4)


def find_similar_incidents(
    incident: Incident,
    store: ReportStore,
    limit: int = 3,
    min_similarity: float = 0.2,
    exclude_report_id: str | None = None,
) -> list[SimilarIncident]:
    """Return up to ``limit`` past reports most similar to ``incident``."""
    candidates, _ = store.list_reports(limit=1000, offset=0)

    scored: list[tuple[float, Report]] = []
    for past in candidates:
        if exclude_report_id and past.id == exclude_report_id:
            continue
        similarity = score_similarity(incident, past)
        if similarity >= min_similarity:
            scored.append((similarity, past))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    return [
        SimilarIncident(
            report_id=past.id,
            incident_title=past.incident.title,
            generated_at=past.generated_at,
            similarity=similarity,
            root_cause_summary=past.root_cause.summary,
            recommended_action=past.root_cause.recommended_action,
        )
        for similarity, past in scored[:limit]
    ]
