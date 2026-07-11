"""Tests for evidence collectors in mock mode."""

from __future__ import annotations

import pytest

from incident_agent.collectors import (
    COLLECTOR_CLASSES,
    GitHubCollector,
    JenkinsCollector,
    KubernetesCollector,
    LokiCollector,
    PrometheusCollector,
    build_collectors,
)
from incident_agent.models import Evidence


def test_build_collectors_returns_all(settings):
    collectors = build_collectors(settings)
    assert len(collectors) == len(COLLECTOR_CLASSES)
    names = {c.name for c in collectors}
    assert names == {"prometheus", "loki", "kubernetes", "github", "jenkins"}


@pytest.mark.parametrize(
    "collector_cls",
    [
        PrometheusCollector,
        LokiCollector,
        KubernetesCollector,
        GitHubCollector,
        JenkinsCollector,
    ],
)
def test_collector_returns_evidence(collector_cls, settings, sample_incident):
    collector = collector_cls(settings)
    evidence = collector.collect(sample_incident)
    assert evidence, f"{collector.name} returned no evidence"
    assert all(isinstance(e, Evidence) for e in evidence)
    assert all(e.source == collector.name for e in evidence)


def test_prometheus_flags_latency_anomaly(settings, sample_incident):
    evidence = PrometheusCollector(settings).collect(sample_incident)
    assert any(e.anomalous and "latency" in e.summary.lower() for e in evidence)


def test_github_flags_recent_deploy(settings, sample_incident):
    evidence = GitHubCollector(settings).collect(sample_incident)
    assert any(e.anomalous for e in evidence)


def test_collectors_not_available_without_config(settings):
    # In mock settings none of the live endpoints are configured.
    for c in build_collectors(settings):
        assert c.available() is False
