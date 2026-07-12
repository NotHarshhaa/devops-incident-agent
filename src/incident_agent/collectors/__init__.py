"""Evidence collectors and a small registry."""

from __future__ import annotations

from ..config import Settings, get_settings
from .alertmanager import AlertmanagerCollector
from .base import Collector
from .github import GitHubCollector
from .jenkins import JenkinsCollector
from .kubernetes import KubernetesCollector
from .loki import LokiCollector
from .prometheus import PrometheusCollector

#: All collectors run during an investigation, in evidence-gathering order.
COLLECTOR_CLASSES: list[type[Collector]] = [
    PrometheusCollector,
    AlertmanagerCollector,
    LokiCollector,
    KubernetesCollector,
    GitHubCollector,
    JenkinsCollector,
]


def build_collectors(settings: Settings | None = None) -> list[Collector]:
    settings = settings or get_settings()
    return [cls(settings) for cls in COLLECTOR_CLASSES]


__all__ = [
    "Collector",
    "PrometheusCollector",
    "AlertmanagerCollector",
    "LokiCollector",
    "KubernetesCollector",
    "GitHubCollector",
    "JenkinsCollector",
    "COLLECTOR_CLASSES",
    "build_collectors",
]
