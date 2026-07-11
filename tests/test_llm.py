"""Tests for the pluggable LLM layer."""

from __future__ import annotations

from incident_agent.config import Settings
from incident_agent.llm import MockProvider, build_llm
from incident_agent.llm.base import LLMProvider
from incident_agent.llm.heuristics import heuristic_root_cause
from incident_agent.llm.prompts import build_user_prompt, parse_root_cause
from incident_agent.models import (
    Evidence,
    EvidenceKind,
    Incident,
    RemediationType,
)


def _deploy_and_db_evidence() -> list[Evidence]:
    return [
        Evidence(
            source="prometheus",
            kind=EvidenceKind.METRIC,
            summary="p99 latency spiked to 8s",
            anomalous=True,
        ),
        Evidence(
            source="loki",
            kind=EvidenceKind.LOG,
            summary="database connection timeout errors",
            anomalous=True,
        ),
        Evidence(
            source="github",
            kind=EvidenceKind.DEPLOYMENT,
            summary="deployment shipped 8 minutes ago",
            anomalous=True,
        ),
    ]


def test_factory_returns_mock_in_mock_mode(settings):
    llm = build_llm(settings)
    assert isinstance(llm, MockProvider)
    assert llm.name == "mock"


def test_factory_falls_back_when_no_api_key():
    s = Settings(mock_mode=False, llm_provider="gemini", gemini_api_key=None)
    llm = build_llm(s)
    assert isinstance(llm, MockProvider)


def test_heuristic_recommends_rollback():
    incident = Incident(title="latency spike")
    rc = heuristic_root_cause(incident, _deploy_and_db_evidence())
    assert rc.recommended_action == RemediationType.ROLLBACK
    assert rc.confidence >= 0.8
    assert rc.contributing_factors


def test_heuristic_detects_oom():
    incident = Incident(title="pods dying")
    evidence = [
        Evidence(source="k8s", summary="Pod OOMKilled", anomalous=True),
    ]
    rc = heuristic_root_cause(incident, evidence)
    assert rc.recommended_action == RemediationType.SCALE


def test_mock_provider_analyze(settings):
    incident = Incident(title="latency spike")
    rc = MockProvider().analyze(incident, _deploy_and_db_evidence())
    assert rc.summary
    assert 0.0 <= rc.confidence <= 1.0


def test_parse_root_cause_handles_fenced_json():
    text = (
        "Here is the result:\n```json\n"
        '{"summary": "bad deploy", "confidence": 0.9, '
        '"recommended_action": "rollback"}\n```'
    )
    rc = parse_root_cause(text)
    assert rc.summary == "bad deploy"
    assert rc.confidence == 0.9
    assert rc.recommended_action == RemediationType.ROLLBACK


def test_parse_root_cause_handles_garbage():
    rc = parse_root_cause("not json at all")
    assert rc.summary == "Undetermined root cause"
    assert rc.confidence == 0.0


def test_build_user_prompt_includes_evidence():
    incident = Incident(title="latency spike", service="api")
    prompt = build_user_prompt(incident, _deploy_and_db_evidence())
    assert "latency spike" in prompt
    assert "database connection timeout" in prompt
    assert "[ANOMALY]" in prompt


class _FakeLLM(LLMProvider):
    """A provider whose complete() returns canned JSON, to test analyze()."""

    name = "fake"

    def __init__(self, payload: str):
        super().__init__("fake-model")
        self._payload = payload

    def complete(self, system: str, user: str) -> str:
        return self._payload


def test_base_analyze_uses_llm_output():
    llm = _FakeLLM('{"summary": "custom cause", "confidence": 0.77, '
                   '"recommended_action": "restart"}')
    rc = llm.analyze(Incident(title="x"), [])
    assert rc.summary == "custom cause"
    assert rc.recommended_action == RemediationType.RESTART


def test_base_analyze_falls_back_on_bad_output():
    llm = _FakeLLM("total garbage, no json")
    rc = llm.analyze(Incident(title="x"), _deploy_and_db_evidence())
    # Falls back to heuristic -> rollback for deploy+db signature.
    assert rc.recommended_action == RemediationType.ROLLBACK
