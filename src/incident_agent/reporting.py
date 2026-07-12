"""Render a :class:`Report` as a Markdown document.

Kept separate from ``cli.py`` so any face (CLI, API, Slack bot, ...) can
reuse the exact same rendering — mirrors the "one pipeline, multiple faces"
principle used for ``run_investigation()`` itself.
"""

from __future__ import annotations

from .models import Report


def report_to_markdown(report: Report) -> str:
    rc = report.root_cause
    incident = report.incident
    lines: list[str] = []

    lines.append(f"# Incident Report — {incident.title}")
    lines.append("")
    lines.append(f"- **Report ID:** `{report.id}`")
    lines.append(f"- **Generated:** {report.generated_at.isoformat()}")
    lines.append(f"- **Severity:** {incident.severity.value}")
    if incident.service:
        lines.append(f"- **Service:** {incident.service}")
    if incident.namespace:
        lines.append(f"- **Namespace:** {incident.namespace}")
    lines.append(f"- **Reasoning provider:** {report.provider}")
    lines.append(f"- **Approved:** {'Yes' if report.approved else 'No'}")
    lines.append("")

    if incident.description:
        lines.append("## Description")
        lines.append("")
        lines.append(incident.description)
        lines.append("")

    lines.append("## Timeline")
    lines.append("")
    if report.timeline:
        for entry in report.timeline:
            lines.append(f"- {entry}")
    else:
        lines.append("_No timeline recorded._")
    lines.append("")

    lines.append("## Root Cause")
    lines.append("")
    lines.append(f"**{rc.summary}**")
    lines.append("")
    lines.append(f"- **Confidence:** {report.confidence_pct()}%")
    lines.append(f"- **Recommended action:** {rc.recommended_action.value.upper()}")
    if rc.recommendation_detail:
        lines.append(f"- **Detail:** {rc.recommendation_detail}")
    if rc.risk:
        lines.append(f"- **Risk:** {rc.risk}")
    lines.append("")

    if rc.contributing_factors:
        lines.append("### Contributing Factors")
        lines.append("")
        for factor in rc.contributing_factors:
            lines.append(f"- {factor}")
        lines.append("")

    if report.similar_incidents:
        lines.append("## Similar Past Incidents")
        lines.append("")
        lines.append("| Report ID | Title | Similarity | Root Cause | Action |")
        lines.append("| --- | --- | --- | --- | --- |")
        for s in report.similar_incidents:
            lines.append(
                f"| `{s.report_id}` | {s.incident_title} | "
                f"{round(s.similarity * 100)}% | {s.root_cause_summary} | "
                f"{s.recommended_action.value} |"
            )
        lines.append("")

    if report.evidence:
        lines.append("## Evidence")
        lines.append("")
        lines.append("| Source | Kind | Anomalous | Summary |")
        lines.append("| --- | --- | --- | --- |")
        for e in report.evidence:
            flag = "⚠️ Yes" if e.anomalous else "No"
            lines.append(f"| {e.source} | {e.kind.value} | {flag} | {e.summary} |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("_Human approval required — nothing was executed automatically._")
    lines.append("")

    return "\n".join(lines)
