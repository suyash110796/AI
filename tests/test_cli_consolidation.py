from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "omega_runtime.cli", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def test_consolidated_cli_help_lists_internal_helpers():
    completed = run_cli("--help")

    assert completed.returncode == 0, completed.stderr
    assert "Consolidated CLI for OMEGA Runtime" in completed.stdout
    for command in (
        "proof-bundle",
        "replay",
        "failure-lab",
        "evidence-pack",
        "release-check",
        "openai",
        "all",
    ):
        assert command in completed.stdout


def test_consolidated_cli_version_returns_machine_readable_json():
    completed = run_cli("--version")

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["accepted"] is True
    assert payload["cli_version"] == "OMEGA_CLI_CONSOLIDATION_V1"
    assert payload["reason"] == "version printed"


def test_consolidated_cli_openai_help_is_available_without_api_key():
    completed = run_cli("openai", "--help")

    assert completed.returncode == 0, completed.stderr
    assert "openai" in completed.stdout.lower()
    assert "--live" in completed.stdout
    assert "--json" in completed.stdout


def test_consolidated_cli_release_check_help_is_available():
    completed = run_cli("release-check", "--help")

    assert completed.returncode == 0, completed.stderr
    assert "release" in completed.stdout.lower()
    assert "--json" in completed.stdout

def test_consolidated_cli_openai_dry_run_executes_without_api_key():
    completed = run_cli("openai", "--dry-run", "--json")

    assert completed.returncode == 0, completed.stderr

    payload = json.loads(completed.stdout)

    assert payload["accepted"] is True
    assert payload["cli_command"] == "openai"
    assert payload["live"] is False
    assert payload["mode"] == "dry_run"
    assert payload["api_key_stored"] is False
    assert "prompt_hash" in payload
    assert "response_hash" in payload


def test_consolidated_cli_openai_auto_records_run_ledger():
    completed = run_cli(
        "openai",
        "--json",
        "--dry-run",
        "--prompt",
        "Ledger auto-record smoke test.",
        "--model",
        "gpt-4.1-mini",
        "--max-output-tokens",
        "300",
    )

    assert completed.returncode == 0, completed.stderr

    payload = json.loads(completed.stdout)

    assert payload["accepted"] is True
    assert payload["ledger_recorded"] is True
    assert payload["ledger_record"]["accepted"] is True
    assert Path(payload["ledger_record"]["record_path"]).exists()
    assert Path(payload["ledger_record"]["ledger_path"]).exists()
    assert payload["ledger_record"]["record_file_sha256"]
