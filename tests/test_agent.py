"""Tests for the agent orchestration (planner + graph)."""

from __future__ import annotations

from incident_agent.agent import make_plan, run_investigation
from incident_agent.models import RemediationType, Report


def test_make_plan_lists_all_sources(settings, sample_incident):
    plan = make_plan(sample_incident, settings)
    joined = " ".join(plan).lower()
    for source in ("prometheus", "loki", "kubernetes", "github", "jenkins"):
        assert source in joined
    assert any("root cause" in step.lower() for step in plan)


def test_run_investigation_sequential(settings, sample_incident):
    report = run_investigation(sample_incident, settings, use_langgraph=False)
    assert isinstance(report, Report)
    assert report.evidence
    assert report.root_cause.summary
    assert report.timeline
    assert report.provider == "mock"


def test_run_investigation_recommends_rollback(settings, sample_incident):
    # The crafted mock evidence (latency + db timeout + recent deploy)
    # should drive the heuristic engine to a ROLLBACK recommendation.
    report = run_investigation(sample_incident, settings, use_langgraph=False)
    assert report.root_cause.recommended_action == RemediationType.ROLLBACK
    assert report.confidence_pct() >= 80


def test_run_investigation_langgraph_or_fallback(settings, sample_incident):
    # Whether or not langgraph is installed, this must succeed and note
    # which orchestrator ran.
    report = run_investigation(sample_incident, settings, use_langgraph=True)
    assert isinstance(report, Report)
    assert any("orchestrator:" in line for line in report.timeline)


def test_report_not_approved_by_default(settings, sample_incident):
    report = run_investigation(sample_incident, settings, use_langgraph=False)
    assert report.approved is False
