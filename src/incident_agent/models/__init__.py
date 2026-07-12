"""Pydantic data models shared across the agent.

These schemas define the contract between collectors, the reasoning engine,
and the API layer:

    Incident  -> the thing we are investigating (input)
    Evidence  -> a single finding from one collector
    RootCause -> the reasoning engine's conclusion
    Report    -> the final human-facing artifact (output)
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class EvidenceKind(str, Enum):
    METRIC = "metric"
    LOG = "log"
    K8S_EVENT = "k8s_event"
    DEPLOYMENT = "deployment"
    CI_CD = "ci_cd"
    OTHER = "other"


class RemediationType(str, Enum):
    ROLLBACK = "rollback"
    SCALE = "scale"
    RESTART = "restart"
    CONFIG_CHANGE = "config_change"
    INVESTIGATE = "investigate"
    NONE = "none"


class Incident(BaseModel):
    """The incident under investigation (agent input)."""

    id: str = Field(default_factory=lambda: _new_id("inc"))
    title: str
    description: str = ""
    severity: Severity = Severity.HIGH
    service: Optional[str] = None
    namespace: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    labels: dict[str, str] = Field(default_factory=dict)


class Evidence(BaseModel):
    """A single finding produced by a collector."""

    source: str                       # collector name, e.g. "prometheus"
    kind: EvidenceKind = EvidenceKind.OTHER
    summary: str                      # short human-readable statement
    detail: Optional[str] = None      # optional longer text
    severity: Severity = Severity.INFO
    anomalous: bool = False           # did the collector flag this as abnormal?
    timestamp: datetime = Field(default_factory=_utcnow)
    raw: dict[str, Any] = Field(default_factory=dict)


class RootCause(BaseModel):
    """The reasoning engine's conclusion."""

    summary: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    contributing_factors: list[str] = Field(default_factory=list)
    recommended_action: RemediationType = RemediationType.INVESTIGATE
    recommendation_detail: str = ""
    risk: str = ""


class SimilarIncident(BaseModel):
    """A past report surfaced as potentially related to the current incident."""

    report_id: str
    incident_title: str
    generated_at: datetime
    similarity: float = Field(ge=0.0, le=1.0)
    root_cause_summary: str
    recommended_action: RemediationType


class Report(BaseModel):
    """The final incident report (agent output)."""

    id: str = Field(default_factory=lambda: _new_id("rpt"))
    incident: Incident
    generated_at: datetime = Field(default_factory=_utcnow)
    evidence: list[Evidence] = Field(default_factory=list)
    root_cause: RootCause
    similar_incidents: list[SimilarIncident] = Field(default_factory=list)
    timeline: list[str] = Field(default_factory=list)
    provider: str = "mock"           # which LLM produced the reasoning
    approved: bool = False           # human-in-the-loop gate

    def confidence_pct(self) -> int:
        return round(self.root_cause.confidence * 100)


# ---- API request / response envelopes ----

class InvestigateRequest(BaseModel):
    title: str = Field(..., description="Short alert/incident title")
    description: str = Field("", description="Free-text details of the incident")
    severity: Severity = Severity.HIGH
    service: Optional[str] = None
    namespace: Optional[str] = None
    labels: dict[str, str] = Field(default_factory=dict)


class ApprovalRequest(BaseModel):
    approved: bool
    note: str = ""


class ReportSummary(BaseModel):
    """Lightweight projection of a Report, used by the listing endpoint."""

    id: str
    incident_title: str
    severity: Severity
    generated_at: datetime
    confidence: float
    recommended_action: RemediationType
    approved: bool

    @classmethod
    def from_report(cls, report: "Report") -> "ReportSummary":
        return cls(
            id=report.id,
            incident_title=report.incident.title,
            severity=report.incident.severity,
            generated_at=report.generated_at,
            confidence=report.root_cause.confidence,
            recommended_action=report.root_cause.recommended_action,
            approved=report.approved,
        )


class ReportListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ReportSummary] = Field(default_factory=list)
