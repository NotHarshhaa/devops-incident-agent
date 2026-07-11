"""Kubernetes events / pod status collector."""

from __future__ import annotations

from ..models import Evidence, EvidenceKind, Incident, Severity
from .base import Collector


class KubernetesCollector(Collector):
    name = "kubernetes"

    def available(self) -> bool:
        # Live mode requires either an explicit kubeconfig or in-cluster creds.
        return bool(self.settings.kubeconfig)

    def _mock(self, incident: Incident) -> list[Evidence]:
        return [
            Evidence(
                source=self.name,
                kind=EvidenceKind.K8S_EVENT,
                summary="All pods Running; no CrashLoopBackOff detected.",
                severity=Severity.INFO,
                anomalous=False,
                raw={"running": 3, "crashloop": 0},
            ),
            Evidence(
                source=self.name,
                kind=EvidenceKind.K8S_EVENT,
                summary="Readiness probe latency elevated on api pods.",
                detail="Probe response times increased alongside request latency.",
                severity=Severity.MEDIUM,
                anomalous=True,
                raw={"probe": "readiness", "status": "slow"},
            ),
        ]

    def _collect_live(self, incident: Incident) -> list[Evidence]:
        from kubernetes import client, config  # lazy

        config.load_kube_config(config_file=self.settings.kubeconfig)
        v1 = client.CoreV1Api()
        namespace = incident.namespace or self.settings.k8s_namespace
        pods = v1.list_namespaced_pod(namespace=namespace)

        evidence: list[Evidence] = []
        crashloop = 0
        running = 0
        for pod in pods.items:
            for cs in pod.status.container_statuses or []:
                waiting = getattr(cs.state, "waiting", None)
                if waiting and waiting.reason == "CrashLoopBackOff":
                    crashloop += 1
            if pod.status.phase == "Running":
                running += 1

        evidence.append(
            Evidence(
                source=self.name,
                kind=EvidenceKind.K8S_EVENT,
                summary=(
                    f"{running} pods Running, {crashloop} in CrashLoopBackOff "
                    f"in namespace '{namespace}'."
                ),
                severity=Severity.HIGH if crashloop else Severity.INFO,
                anomalous=crashloop > 0,
                raw={"running": running, "crashloop": crashloop},
            )
        )
        return evidence
