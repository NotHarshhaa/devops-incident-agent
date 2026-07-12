"""Tests for the Markdown report renderer."""

from __future__ import annotations

from incident_agent.models import (
    Incident,
    RemediationType,
    Report,
    RootCause,
    SimilarIncident,
)
from incident_agent.reporting import report_to_markdown


def _sample_report() -> Report:
    incident = Incident(title="Latency spike", service="api", description="Checkout is slow")
    root_cause = RootCause(
        summary="Recent deploy caused a DB regression",
        confidence=0.9,
        contributing_factors=["p99 latency spiked", "DB timeouts"],
        recommended_action=RemediationType.ROLLBACK,
        recommendation_detail="Roll back to the previous release",
        risk="Low",
    )
    report = Report(
        incident=incident,
        root_cause=root_cause,
        timeline=["🚨 Alert received", "→ reasoning: done"],
        similar_incidents=[
            SimilarIncident(
                report_id="rpt_abc123",
                incident_title="Latency spike last week",
                generated_at=incident.created_at,
                similarity=0.85,
                root_cause_summary="Same DB regression",
                recommended_action=RemediationType.ROLLBACK,
            )
        ],
    )
    return report


def test_report_to_markdown_includes_key_sections():
    md = report_to_markdown(_sample_report())
    assert md.startswith("# Incident Report — Latency spike")
    assert "## Timeline" in md
    assert "## Root Cause" in md
    assert "Recent deploy caused a DB regression" in md
    assert "## Contributing Factors" in md
    assert "## Similar Past Incidents" in md
    assert "rpt_abc123" in md
    assert "ROLLBACK" in md
    assert "90%" in md


def test_report_to_markdown_handles_no_evidence_or_similar_incidents():
    incident = Incident(title="Quiet incident")
    report = Report(incident=incident, root_cause=RootCause(summary="unknown", confidence=0.2))
    md = report_to_markdown(report)
    assert "# Incident Report — Quiet incident" in md
    assert "## Evidence" not in md
    assert "## Similar Past Incidents" not in md
    assert "_No timeline recorded._" in md
