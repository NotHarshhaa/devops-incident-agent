"""Rule-based (offline) root-cause reasoning.

Used by the ``mock`` LLM provider and as a fallback when a real provider
fails to return valid JSON. It applies simple, explainable SRE heuristics
over the collected evidence so the agent produces a useful report even with
no API key and no live infrastructure.
"""

from __future__ import annotations

from ..models import (
    Evidence,
    EvidenceKind,
    Incident,
    RemediationType,
    RootCause,
)


def heuristic_root_cause(incident: Incident, evidence: list[Evidence]) -> RootCause:
    anomalies = [e for e in evidence if e.anomalous]
    text_blob = " ".join(
        f"{e.summary} {e.detail or ''}" for e in evidence
    ).lower()

    has_recent_deploy = any(
        e.kind == EvidenceKind.DEPLOYMENT and e.anomalous for e in evidence
    )
    has_ci_failure = any(
        e.kind == EvidenceKind.CI_CD and e.anomalous for e in evidence
    )
    db_signal = any(
        kw in text_blob for kw in ("database", "db timeout", "connection pool", "sql")
    )
    oom_signal = "oom" in text_blob or "out of memory" in text_blob
    crashloop_signal = "crashloop" in text_blob or "backoff" in text_blob
    latency_signal = "latency" in text_blob or "slow" in text_blob or "timeout" in text_blob

    factors = [e.summary for e in anomalies] or [
        "No clear anomaly detected in the collected evidence"
    ]

    # ---- Decision tree (ordered by specificity) ----
    if has_recent_deploy and (db_signal or latency_signal):
        return RootCause(
            summary=(
                "A recent deployment likely introduced a regression "
                "(configuration or code change) that degraded the service."
            ),
            confidence=0.9,
            contributing_factors=factors,
            recommended_action=RemediationType.ROLLBACK,
            recommendation_detail=(
                "Roll back to the previous known-good release and confirm "
                "the symptom clears, then investigate the diff."
            ),
            risk="Low — rolling back to a previously validated version.",
        )

    if oom_signal:
        return RootCause(
            summary="Pods are being OOM-killed due to insufficient memory limits.",
            confidence=0.82,
            contributing_factors=factors,
            recommended_action=RemediationType.SCALE,
            recommendation_detail=(
                "Increase the memory limit/request for the affected workload "
                "or scale out replicas, then profile memory usage."
            ),
            risk="Low-medium — raises resource consumption on the cluster.",
        )

    if crashloop_signal:
        return RootCause(
            summary="One or more pods are in CrashLoopBackOff and failing to start.",
            confidence=0.78,
            contributing_factors=factors,
            recommended_action=RemediationType.RESTART,
            recommendation_detail=(
                "Inspect the crashing container's logs and readiness probe, "
                "fix the startup error, then restart the deployment."
            ),
            risk="Low — restart affects only the already-failing workload.",
        )

    if has_ci_failure:
        return RootCause(
            summary="A failing CI/CD pipeline likely shipped a broken artifact.",
            confidence=0.7,
            contributing_factors=factors,
            recommended_action=RemediationType.ROLLBACK,
            recommendation_detail=(
                "Roll back to the last successful pipeline artifact and "
                "block further promotion until the pipeline is green."
            ),
            risk="Low — reverts to the last successful build.",
        )

    if db_signal:
        return RootCause(
            summary="A database dependency appears degraded (timeouts/pool exhaustion).",
            confidence=0.65,
            contributing_factors=factors,
            recommended_action=RemediationType.INVESTIGATE,
            recommendation_detail=(
                "Check database connection pool sizing, slow queries and "
                "DB-side resource saturation."
            ),
            risk="N/A — investigation only.",
        )

    if anomalies:
        return RootCause(
            summary=(
                "Multiple anomalies detected but no single dominant cause; "
                "manual correlation needed."
            ),
            confidence=0.45,
            contributing_factors=factors,
            recommended_action=RemediationType.INVESTIGATE,
            recommendation_detail=(
                "Correlate the flagged anomalies on a shared timeline to "
                "isolate the trigger."
            ),
            risk="N/A — investigation only.",
        )

    return RootCause(
        summary="No anomalies detected in the collected evidence.",
        confidence=0.2,
        contributing_factors=factors,
        recommended_action=RemediationType.INVESTIGATE,
        recommendation_detail=(
            "Broaden the evidence window or add more data sources; the "
            "current signals look nominal."
        ),
        risk="N/A — investigation only.",
    )
