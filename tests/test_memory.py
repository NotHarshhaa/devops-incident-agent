"""Tests for incident memory (similar past incident lookup)."""

from __future__ import annotations

from incident_agent.agent.memory import find_similar_incidents, score_similarity
from incident_agent.models import Incident, Report, RootCause, Severity
from incident_agent.store import ReportStore


def _report(title: str, service: str | None, severity: Severity, summary: str) -> Report:
    return Report(
        incident=Incident(title=title, service=service, severity=severity),
        root_cause=RootCause(summary=summary, confidence=0.8),
    )


def test_score_similarity_high_for_near_identical_titles():
    incident = Incident(title="Production API latency spike", service="api")
    past = _report(
        "Production API latency spike again",
        "api",
        Severity.HIGH,
        "same as before",
    )
    score = score_similarity(incident, past)
    assert score > 0.7


def test_score_similarity_low_for_unrelated_incidents():
    incident = Incident(title="Production API latency spike", service="api")
    past = _report(
        "Billing export job failed silently",
        "billing",
        Severity.LOW,
        "unrelated",
    )
    score = score_similarity(incident, past)
    assert score < 0.2


def test_find_similar_incidents_returns_closest_matches(settings):
    store = ReportStore(settings)
    store.save(_report("Checkout API latency spike", "api", Severity.HIGH, "deploy regression"))
    store.save(_report("Billing job failed", "billing", Severity.LOW, "unrelated"))
    store.save(_report("API latency spike again", "api", Severity.HIGH, "deploy regression"))

    incident = Incident(title="API latency spike", service="api", severity=Severity.HIGH)
    similar = find_similar_incidents(incident, store, limit=2)

    assert len(similar) <= 2
    assert all(s.similarity >= 0.2 for s in similar)
    # Sorted descending by similarity.
    assert similar == sorted(similar, key=lambda s: s.similarity, reverse=True)


def test_find_similar_incidents_excludes_given_report_id(settings):
    store = ReportStore(settings)
    report = _report("API latency spike", "api", Severity.HIGH, "deploy regression")
    store.save(report)

    incident = Incident(title="API latency spike", service="api", severity=Severity.HIGH)
    similar = find_similar_incidents(incident, store, exclude_report_id=report.id)

    assert all(s.report_id != report.id for s in similar)


def test_find_similar_incidents_empty_store_returns_empty(settings):
    store = ReportStore(settings)
    incident = Incident(title="Something new")
    assert find_similar_incidents(incident, store) == []
