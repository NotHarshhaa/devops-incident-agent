"""GitHub deployments / recent commits collector."""

from __future__ import annotations

from ..models import Evidence, EvidenceKind, Incident, Severity
from .base import Collector


class GitHubCollector(Collector):
    name = "github"

    def available(self) -> bool:
        return bool(self.settings.github_token and self.settings.github_repo)

    def _mock(self, incident: Incident) -> list[Evidence]:
        return [
            Evidence(
                source=self.name,
                kind=EvidenceKind.DEPLOYMENT,
                summary="Deployment shipped 8 minutes ago (commit a1b2c3d).",
                detail=(
                    "PR #412 'tune DB connection pool' merged to main; "
                    "changed SQLALCHEMY_POOL_SIZE from 20 to 5."
                ),
                severity=Severity.HIGH,
                anomalous=True,
                raw={
                    "sha": "a1b2c3d",
                    "pr": 412,
                    "title": "tune DB connection pool",
                    "minutes_ago": 8,
                },
            ),
        ]

    def _collect_live(self, incident: Incident) -> list[Evidence]:
        import httpx  # lazy

        repo = self.settings.github_repo
        headers = {
            "Authorization": f"Bearer {self.settings.github_token}",
            "Accept": "application/vnd.github+json",
        }
        with httpx.Client(timeout=10.0, headers=headers) as client:
            resp = client.get(
                f"https://api.github.com/repos/{repo}/commits",
                params={"per_page": 5},
            )
            resp.raise_for_status()
            commits = resp.json()

        evidence: list[Evidence] = []
        for c in commits[:5]:
            message = c.get("commit", {}).get("message", "").splitlines()[0]
            sha = c.get("sha", "")[:7]
            evidence.append(
                Evidence(
                    source=self.name,
                    kind=EvidenceKind.DEPLOYMENT,
                    summary=f"Recent commit {sha}: {message}",
                    severity=Severity.INFO,
                    anomalous=False,
                    raw={"sha": sha, "message": message},
                )
            )
        if evidence:
            # Treat the most recent commit as a potential deploy trigger.
            evidence[0].anomalous = True
            evidence[0].severity = Severity.MEDIUM
        return evidence
