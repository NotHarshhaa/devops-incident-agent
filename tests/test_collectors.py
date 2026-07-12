"""Tests for evidence collectors in mock mode."""

from __future__ import annotations

import pytest

from incident_agent.collectors import (
    COLLECTOR_CLASSES,
    AlertmanagerCollector,
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
    assert names == {
        "prometheus",
        "alertmanager",
        "loki",
        "kubernetes",
        "github",
        "jenkins",
    }


@pytest.mark.parametrize(
    "collector_cls",
    [
        PrometheusCollector,
        AlertmanagerCollector,
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


def test_alertmanager_flags_firing_critical_alert(settings, sample_incident):
    evidence = AlertmanagerCollector(settings).collect(sample_incident)
    assert any(e.anomalous for e in evidence)


def test_alertmanager_available_with_url(settings):
    settings.alertmanager_url = "http://localhost:9093"
    assert AlertmanagerCollector(settings).available() is True


def test_collectors_not_available_without_config(settings):
    # In mock settings none of the live endpoints are configured.
    for c in build_collectors(settings):
        assert c.available() is False


def test_kubernetes_available_with_kubeconfig(settings):
    settings.kubeconfig = "/some/path/kubeconfig.yaml"
    assert KubernetesCollector(settings).available() is True


def test_kubernetes_available_in_cluster(settings, monkeypatch):
    # No explicit kubeconfig, but running with an in-cluster service account
    # token should still report available (regression: previously only
    # checked `kubeconfig`, ignoring in-cluster credentials).
    collector = KubernetesCollector(settings)
    monkeypatch.setattr(collector, "_in_cluster", lambda: True)
    assert collector.available() is True


def test_kubernetes_unavailable_without_kubeconfig_or_incluster(settings, monkeypatch):
    collector = KubernetesCollector(settings)
    monkeypatch.setattr(collector, "_in_cluster", lambda: False)
    assert collector.available() is False
