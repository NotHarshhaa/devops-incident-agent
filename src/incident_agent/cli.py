"""Command-line interface.

Usage:
    incident-agent "Production API latency increased to 8 seconds"
    python -m incident_agent.cli "..." --service api --severity critical
    incident-agent --serve          # run the API server
"""

from __future__ import annotations

import argparse
import sys

from .agent import run_investigation
from .config import get_settings
from .models import Incident, Severity


def _print_report(report) -> None:
    rc = report.root_cause
    print("\n" + "=" * 68)
    print(f"🚨 INCIDENT REPORT  ({report.id})")
    print("=" * 68)
    print(f"Incident : {report.incident.title}")
    print(f"Provider : {report.provider}")
    print("\n--- Timeline ---")
    for line in report.timeline:
        print(f"  {line}")
    print("\n--- Root Cause ---")
    print(f"  {rc.summary}")
    print(f"  Confidence     : {report.confidence_pct()}%")
    if rc.contributing_factors:
        print("  Contributing factors:")
        for f in rc.contributing_factors:
            print(f"    - {f}")
    print(f"  Recommendation : {rc.recommended_action.value.upper()}")
    if rc.recommendation_detail:
        print(f"    {rc.recommendation_detail}")
    if rc.risk:
        print(f"  Risk           : {rc.risk}")
    print("=" * 68)
    print("Human approval required — nothing was executed.\n")


def _ensure_utf8_stdout() -> None:
    """Best-effort switch stdout to UTF-8 so emoji don't crash cp1252 consoles."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdout()
    parser = argparse.ArgumentParser(prog="incident-agent")
    parser.add_argument("title", nargs="?", help="Incident/alert title")
    parser.add_argument("--description", default="")
    parser.add_argument("--service", default=None)
    parser.add_argument("--namespace", default=None)
    parser.add_argument(
        "--severity",
        default="high",
        choices=[s.value for s in Severity],
    )
    parser.add_argument("--serve", action="store_true", help="Run the API server")
    args = parser.parse_args(argv)

    if args.serve:
        import uvicorn

        settings = get_settings()
        uvicorn.run(
            "incident_agent.main:app",
            host=settings.host,
            port=settings.port,
            reload=False,
        )
        return 0

    if not args.title:
        parser.error("provide an incident title, or use --serve to run the API")

    incident = Incident(
        title=args.title,
        description=args.description,
        severity=Severity(args.severity),
        service=args.service,
        namespace=args.namespace,
    )
    report = run_investigation(incident)
    _print_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
