"""Alertmanager active-alerts collector."""

from __future__ import annotations

from ..models import Evidence, EvidenceKind, Incident, Severity
from .base import Collector

#: Alertmanager severities that should be treated as anomalous findings.
_ANOMALOUS_SEVERITIES = {"critical", "warning", "page"}


class AlertmanagerCollector(Collector):
    name = "alertmanager"

    def available(self) -> bool:
        return bool(self.settings.alertmanager_url)

    def _mock(self, incident: Incident) -> list[Evidence]:
        service = incident.service or "api"
        return [
            Evidence(
                source=self.name,
                kind=EvidenceKind.OTHER,
                summary=f"Firing alert 'HighLatency' for service '{service}'.",
                detail=(
                    "labels: severity=critical, service="
                    f"{service} | annotations: p99 latency above SLO for 5m"
                ),
                severity=Severity.CRITICAL,
                anomalous=True,
                raw={"alertname": "HighLatency", "status": "firing", "severity": "critical"},
            ),
            Evidence(
                source=self.name,
                kind=EvidenceKind.OTHER,
                summary="Alert 'DeploymentRolloutStuck' resolved 3 minutes ago.",
                severity=Severity.INFO,
                anomalous=False,
                raw={"alertname": "DeploymentRolloutStuck", "status": "resolved"},
            ),
        ]

    def _collect_live(self, incident: Incident) -> list[Evidence]:
        import httpx  # lazy

        base = self.settings.alertmanager_url.rstrip("/")
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{base}/api/v2/alerts", params={"active": "true"})
            resp.raise_for_status()
            alerts = resp.json()

        evidence: list[Evidence] = []
        for alert in alerts:
            labels = alert.get("labels", {}) or {}
            annotations = alert.get("annotations", {}) or {}
            status = (alert.get("status", {}) or {}).get("state", "unknown")
            alertname = labels.get("alertname", "unknown")
            severity_label = labels.get("severity", "info").lower()
            firing = status == "active"
            anomalous = firing and severity_label in _ANOMALOUS_SEVERITIES

            summary = f"Alert '{alertname}' is {status}"
            if labels.get("service"):
                summary += f" (service: {labels['service']})"
            detail = annotations.get("description") or annotations.get("summary")

            evidence.append(
                Evidence(
                    source=self.name,
                    kind=EvidenceKind.OTHER,
                    summary=summary,
                    detail=detail,
                    severity=Severity.CRITICAL if anomalous else Severity.INFO,
                    anomalous=anomalous,
                    raw={"alertname": alertname, "status": status, "labels": labels},
                )
            )
        return evidence
