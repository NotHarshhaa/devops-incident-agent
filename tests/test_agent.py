"""Tests for the agent orchestration (planner + graph)."""

from __future__ import annotations

import pytest

from incident_agent.agent import make_plan, run_investigation
from incident_agent.agent.graph import (
    LOW_CONFIDENCE_THRESHOLD,
    MAX_RECOLLECTIONS,
    _needs_recollection,
)
from incident_agent.llm.base import LLMProvider
from incident_agent.models import Incident, RemediationType, Report, RootCause


def test_make_plan_lists_all_sources(settings, sample_incident):
    plan = make_plan(sample_incident, settings)
    joined = " ".join(plan).lower()
    for source in ("prometheus", "alertmanager", "loki", "kubernetes", "github", "jenkins"):
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


def test_report_includes_similar_incidents_field(settings, sample_incident):
    report = run_investigation(sample_incident, settings, use_langgraph=False)
    assert isinstance(report.similar_incidents, list)
    assert any("memory:" in line for line in report.timeline)


def test_needs_recollection_true_below_threshold():
    state = {"root_cause": RootCause(summary="x", confidence=LOW_CONFIDENCE_THRESHOLD - 0.01)}
    assert _needs_recollection(state) is True


def test_needs_recollection_false_at_or_above_threshold():
    state = {"root_cause": RootCause(summary="x", confidence=LOW_CONFIDENCE_THRESHOLD)}
    assert _needs_recollection(state) is False


def test_needs_recollection_false_once_max_retries_reached():
    state = {
        "root_cause": RootCause(summary="x", confidence=0.1),
        "recollect_count": MAX_RECOLLECTIONS,
    }
    assert _needs_recollection(state) is False


class _LowConfidenceLLM(LLMProvider):
    """Always returns a low-confidence root cause, to exercise the re-collect loop."""

    name = "low-confidence-fake"

    def __init__(self):
        super().__init__("fake-model")

    def complete(self, system: str, user: str) -> str:  # pragma: no cover - unused
        return "{}"

    def analyze(self, incident: Incident, evidence):
        return RootCause(summary="inconclusive", confidence=0.1)


@pytest.mark.parametrize("use_langgraph", [False, True])
def test_low_confidence_triggers_single_recollection(
    monkeypatch, settings, sample_incident, use_langgraph
):
    monkeypatch.setattr(
        "incident_agent.agent.graph.build_llm", lambda settings: _LowConfidenceLLM()
    )
    report = run_investigation(sample_incident, settings, use_langgraph=use_langgraph)

    recollect_notes = [line for line in report.timeline if "re-collecting evidence" in line]
    assert len(recollect_notes) == 1, "should re-collect exactly once, never loop forever"
    assert report.root_cause.confidence == 0.1

    # Evidence collected twice (initial + one re-collection) means roughly
    # double the findings compared to a single collection pass.
    single_pass_count = len(report.evidence) // 2
    assert single_pass_count > 0
