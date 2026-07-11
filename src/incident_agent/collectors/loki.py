"""Loki log collector."""

from __future__ import annotations

from ..models import Evidence, EvidenceKind, Incident, Severity
from .base import Collector


class LokiCollector(Collector):
    name = "loki"

    def available(self) -> bool:
        return bool(self.settings.loki_url)

    def _mock(self, incident: Incident) -> list[Evidence]:
        return [
            Evidence(
                source=self.name,
                kind=EvidenceKind.LOG,
                summary="High volume of 'database connection timeout' errors.",
                detail=(
                    "142 occurrences in 5m of "
                    "'psycopg2.OperationalError: connection timed out' "
                    "from the api service."
                ),
                severity=Severity.HIGH,
                anomalous=True,
                raw={"error": "database connection timeout", "count": 142},
            ),
            Evidence(
                source=self.name,
                kind=EvidenceKind.LOG,
                summary="Connection pool exhausted warnings observed.",
                detail="'QueuePool limit of size 5 overflow 10 reached'",
                severity=Severity.HIGH,
                anomalous=True,
                raw={"warning": "connection pool exhausted", "count": 37},
            ),
        ]

    def _collect_live(self, incident: Incident) -> list[Evidence]:
        import httpx  # lazy

        base = self.settings.loki_url.rstrip("/")
        service = incident.service or "api"
        query = f'{{app="{service}"}} |~ "(?i)error|timeout|exception"'
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{base}/loki/api/v1/query_range",
                params={"query": query, "limit": 100},
            )
            resp.raise_for_status()
            streams = resp.json().get("data", {}).get("result", [])
        total = sum(len(s.get("values", [])) for s in streams)
        return [
            Evidence(
                source=self.name,
                kind=EvidenceKind.LOG,
                summary=f"{total} error/timeout log lines matched for '{service}'.",
                severity=Severity.HIGH if total else Severity.INFO,
                anomalous=total > 0,
                raw={"matched_lines": total, "query": query},
            )
        ]
