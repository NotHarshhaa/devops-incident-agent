"""Jenkins CI/CD pipeline collector."""

from __future__ import annotations

from ..models import Evidence, EvidenceKind, Incident, Severity
from .base import Collector


class JenkinsCollector(Collector):
    name = "jenkins"

    def available(self) -> bool:
        return bool(self.settings.jenkins_url)

    def _mock(self, incident: Incident) -> list[Evidence]:
        return [
            Evidence(
                source=self.name,
                kind=EvidenceKind.CI_CD,
                summary="Latest pipeline build #338 SUCCESS.",
                detail="Deploy stage completed 9 minutes ago.",
                severity=Severity.INFO,
                anomalous=False,
                raw={"build": 338, "result": "SUCCESS"},
            ),
        ]

    def _collect_live(self, incident: Incident) -> list[Evidence]:
        import httpx  # lazy

        base = self.settings.jenkins_url.rstrip("/")
        auth = None
        if self.settings.jenkins_user and self.settings.jenkins_token:
            auth = (self.settings.jenkins_user, self.settings.jenkins_token)
        with httpx.Client(timeout=10.0, auth=auth) as client:
            resp = client.get(f"{base}/api/json?tree=jobs[name,lastBuild[number,result]]")
            resp.raise_for_status()
            jobs = resp.json().get("jobs", [])

        evidence: list[Evidence] = []
        for job in jobs:
            last = job.get("lastBuild") or {}
            result = last.get("result")
            failed = result not in (None, "SUCCESS")
            evidence.append(
                Evidence(
                    source=self.name,
                    kind=EvidenceKind.CI_CD,
                    summary=(
                        f"Job '{job.get('name')}' build #{last.get('number')}: "
                        f"{result or 'RUNNING'}"
                    ),
                    severity=Severity.HIGH if failed else Severity.INFO,
                    anomalous=failed,
                    raw={"job": job.get("name"), "result": result},
                )
            )
        return evidence
