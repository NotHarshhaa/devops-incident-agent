"""Prometheus metrics collector."""

from __future__ import annotations

from ..models import Evidence, EvidenceKind, Incident, Severity
from .base import Collector


class PrometheusCollector(Collector):
    name = "prometheus"

    def available(self) -> bool:
        return bool(self.settings.prometheus_url)

    def _mock(self, incident: Incident) -> list[Evidence]:
        return [
            Evidence(
                source=self.name,
                kind=EvidenceKind.METRIC,
                summary="CPU utilization nominal (~35%), within normal range.",
                severity=Severity.INFO,
                anomalous=False,
                raw={"metric": "cpu_usage", "value": 0.35},
            ),
            Evidence(
                source=self.name,
                kind=EvidenceKind.METRIC,
                summary="Memory utilization nominal (~48%).",
                severity=Severity.INFO,
                anomalous=False,
                raw={"metric": "memory_usage", "value": 0.48},
            ),
            Evidence(
                source=self.name,
                kind=EvidenceKind.METRIC,
                summary="p99 request latency spiked to 8.1s (baseline ~180ms).",
                detail="http_request_duration_seconds p99 rose 45x over baseline.",
                severity=Severity.CRITICAL,
                anomalous=True,
                raw={"metric": "latency_p99_seconds", "value": 8.1, "baseline": 0.18},
            ),
        ]

    def _collect_live(self, incident: Incident) -> list[Evidence]:
        import httpx  # lazy

        base = self.settings.prometheus_url.rstrip("/")
        queries = {
            "latency_p99_seconds": (
                'histogram_quantile(0.99, sum(rate('
                'http_request_duration_seconds_bucket[5m])) by (le))'
            ),
            "cpu_usage": 'avg(rate(process_cpu_seconds_total[5m]))',
        }
        evidence: list[Evidence] = []
        with httpx.Client(timeout=10.0) as client:
            for metric, promql in queries.items():
                resp = client.get(
                    f"{base}/api/v1/query", params={"query": promql}
                )
                resp.raise_for_status()
                result = resp.json().get("data", {}).get("result", [])
                value = float(result[0]["value"][1]) if result else 0.0
                anomalous = metric == "latency_p99_seconds" and value > 1.0
                evidence.append(
                    Evidence(
                        source=self.name,
                        kind=EvidenceKind.METRIC,
                        summary=f"{metric} = {value:g}",
                        severity=Severity.CRITICAL if anomalous else Severity.INFO,
                        anomalous=anomalous,
                        raw={"metric": metric, "value": value},
                    )
                )
        return evidence
