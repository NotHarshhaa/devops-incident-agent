"""HTTP API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..agent import run_investigation
from ..config import get_settings
from ..models import (
    ApprovalRequest,
    Incident,
    InvestigateRequest,
    Report,
)
from ..store import get_store

router = APIRouter()


@router.get("/health", tags=["system"])
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "mock_mode": settings.mock_mode,
        "llm_provider": settings.effective_provider(),
    }


@router.post("/investigate", response_model=Report, tags=["incidents"])
def investigate(req: InvestigateRequest) -> Report:
    """Run a full incident investigation and return a root-cause report."""
    incident = Incident(
        title=req.title,
        description=req.description,
        severity=req.severity,
        service=req.service,
        namespace=req.namespace,
        labels=req.labels,
    )
    report = run_investigation(incident)
    get_store().save(report)
    return report


@router.get("/reports/{report_id}", response_model=Report, tags=["incidents"])
def get_report(report_id: str) -> Report:
    report = get_store().get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post(
    "/reports/{report_id}/approval", response_model=Report, tags=["incidents"]
)
def approve_report(report_id: str, req: ApprovalRequest) -> Report:
    """Human-in-the-loop gate. Nothing auto-executes; this records approval."""
    store = get_store()
    report = store.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    report.approved = req.approved
    if req.note:
        report.timeline.append(
            f"→ human {'approved' if req.approved else 'rejected'}: {req.note}"
        )
    else:
        report.timeline.append(
            f"→ human {'approved' if req.approved else 'rejected'} the recommendation"
        )
    store.save(report)
    return report
