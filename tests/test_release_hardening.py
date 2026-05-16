from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run_release_check() -> dict:
    completed = subprocess.run(
        [sys.executable, "scripts/release_check.py", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr + completed.stdout
    return json.loads(completed.stdout)


def test_pyproject_is_final_1_0_0():
    pyproject = tomllib.loads(
        (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert pyproject["project"]["version"] == "1.0.0"


def test_release_check_accepts_final_release():
    payload = _run_release_check()

    assert payload["accepted"] is True
    assert payload["release_version"] == "1.0.0"
    assert payload["checks_failed"] == 0
    assert payload["reason"] == "release check passed"


def test_release_check_requires_rc1_milestone_tag():
    payload = _run_release_check()

    assert "v1.0.0-rc1-release-hardening" in payload["milestone_tags"]

    milestone_check = next(
        check for check in payload["checks"] if check["name"] == "milestone_tags"
    )

    assert milestone_check["accepted"] is True
    assert "v1.0.0-rc1-release-hardening" in milestone_check["detail"]["required_tags"]


def test_release_scripts_and_evidence_pack_are_present():
    payload = _run_release_check()

    required_files_check = next(
        check for check in payload["checks"] if check["name"] == "required_files"
    )

    release_scripts_check = next(
        check for check in payload["checks"] if check["name"] == "release_scripts"
    )

    required_files = set(required_files_check["detail"]["required_files"])
    required_scripts = set(release_scripts_check["detail"]["required_scripts"])

    assert "scripts/demo_evidence_pack.py" in required_files
    assert "scripts/release_check.py" in required_files
    assert "scripts/release_check.py" in required_scripts
