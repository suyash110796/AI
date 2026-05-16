from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from omega_runtime.release_check import (
    RELEASE_CHECK_VERSION,
    RELEASE_VERSION,
    run_release_check,
    write_release_report,
)

def test_release_check_manifest_shape():
    report = run_release_check()

    assert report["release_check_version"] == RELEASE_CHECK_VERSION
    assert report["release_version"] == RELEASE_VERSION
    assert "README.md" in report["required_files"]
    assert "omega_runtime/api.py" in report["required_files"]
    assert "tests" in report["required_directories"]
    assert "v0.9.0-evidence-pack-ui" in report["milestone_tags"]
    assert "aggregate_hash" in report

def test_release_check_passes_for_current_tree():
    report = run_release_check()

    assert report["accepted"] is True
    assert report["reason"] == "release check passed"
    assert report["checks_failed"] == 0
    assert report["checks_passed"] == report["checks_total"]

def test_release_report_can_be_written(tmp_path):
    out = tmp_path / "release_check_report.json"
    report = write_release_report(out)

    assert out.exists()

    payload = json.loads(out.read_text(encoding="utf-8"))

    assert report["accepted"] is True
    assert payload["accepted"] is True
    assert payload["release_check_version"] == "OMEGA_RELEASE_CHECK_V1"
    assert payload["release_version"] == "1.0.0rc1"

def test_release_check_script_runs_json():
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/release_check.py",
            "--json",
            "--out",
            "artifacts/release/test_release_check_report.json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr

    payload = json.loads(completed.stdout)

    assert payload["accepted"] is True
    assert payload["reason"] == "release check passed"
    assert payload["release_version"] == "1.0.0rc1"
