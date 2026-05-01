from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from omega_runtime.core.auditor import audit_artifacts, write_audit_report


def test_auditor_rejects_no_artifacts():
    payload = audit_artifacts()

    assert payload["audit_type"] == "OMEGA_AUDITOR_V1"
    assert payload["accepted"] is False
    assert payload["reason"] == "no artifacts supplied"
    assert payload["artifact_count"] == 0
    assert payload["items"] == []
    assert payload["aggregate_hash"] is not None


def test_auditor_writes_report(tmp_path):
    report_path = tmp_path / "audit_report.json"

    payload = write_audit_report(path=report_path)

    assert report_path.exists()
    saved = json.loads(report_path.read_text(encoding="utf-8"))

    assert saved["accepted"] is False
    assert saved["reason"] == "no artifacts supplied"
    assert saved["aggregate_hash"] == payload["aggregate_hash"]


def test_audit_cli_json_no_artifacts():
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/audit_runtime.py",
            "--json",
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 1

    payload = json.loads(completed.stdout)

    assert payload["accepted"] is False
    assert payload["reason"] == "no artifacts supplied"
    assert payload["artifact_count"] == 0


def test_audit_cli_writes_report(tmp_path):
    report_path = tmp_path / "audit_report.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/audit_runtime.py",
            "--out",
            str(report_path),
            "--json",
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 1
    assert report_path.exists()

    stdout_payload = json.loads(completed.stdout)
    saved_payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert stdout_payload["aggregate_hash"] == saved_payload["aggregate_hash"]
    assert saved_payload["reason"] == "no artifacts supplied"
