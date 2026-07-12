"""Tests for the CLI entrypoint."""

from __future__ import annotations

from incident_agent.cli import main


def test_main_runs_investigation_and_prints_report(capsys):
    exit_code = main(["Latency spike", "--service", "api"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "INCIDENT REPORT" in captured.out
    assert "Root Cause" in captured.out


def test_main_without_title_or_serve_errors(capsys):
    try:
        main([])
    except SystemExit as exc:
        assert exc.code != 0
    else:
        raise AssertionError("expected argparse to exit when no title/--serve given")


def test_main_writes_markdown_report_with_output_flag(tmp_path):
    output_path = tmp_path / "report.md"
    exit_code = main(["Latency spike", "--service", "api", "--output", str(output_path)])

    assert exit_code == 0
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert content.startswith("# Incident Report — Latency spike")
    assert "## Root Cause" in content


def test_main_output_flag_creates_parent_directories(tmp_path):
    output_path = tmp_path / "nested" / "dir" / "report.md"
    exit_code = main(["Latency spike", "--output", str(output_path)])

    assert exit_code == 0
    assert output_path.exists()
