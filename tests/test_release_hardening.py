from __future__ import annotations

import re
import sys
import subprocess
import json
from pathlib import Path

import omega_runtime.release_check as release_check


EXPECTED_RELEASE_VERSION = "1.3.0"

EXPECTED_MILESTONE_TAGS = [
    "v0.1.0-stable",
    "v0.2.0-cli-packaging",
    "v0.3.0-api",
    "v0.4.0-ui-dashboard-complete",
    "v0.5.0-failure-lab",
    "v0.6.0-failure-lab-dashboard",
    "v0.7.0-agent-action-playground",
    "v0.8.0-evidence-pack",
    "v0.9.0-evidence-pack-ui",
    "v1.0.0-rc1-release-hardening",
    "v1.0.0",
    "v1.2.0-cli-consolidation",
]


def _pyproject_version() -> str:
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)

    assert match is not None, "pyproject.toml must contain a version field"
    return match.group(1)


def _module_release_version() -> str:
    value = getattr(release_check, "RELEASE_VERSION", None)

    assert value is not None, "omega_runtime.release_check must expose RELEASE_VERSION"
    return str(value)


def _module_required_tags() -> list[str]:
    for name in (
        "REQUIRED_MILESTONE_TAGS",
        "MILESTONE_TAGS",
        "REQUIRED_TAGS",
    ):
        value = getattr(release_check, name, None)

        if value is not None:
            return list(value)

    raise AssertionError(
        "omega_runtime.release_check must expose REQUIRED_MILESTONE_TAGS, "
        "MILESTONE_TAGS, or REQUIRED_TAGS"
    )


def _run_release_check() -> dict:
    for name in (
        "run_release_check",
        "build_release_check",
        "generate_release_check",
        "check_release",
    ):
        fn = getattr(release_check, name, None)

        if callable(fn):
            result = fn()

            if hasattr(result, "dict"):
                result = result.dict()

            assert isinstance(result, dict), f"{name} must return a dict-like report"
            return result

    raise AssertionError("omega_runtime.release_check must expose a release check runner")


def test_release_version_matches_pyproject():
    assert _pyproject_version() == EXPECTED_RELEASE_VERSION
    assert _module_release_version() == EXPECTED_RELEASE_VERSION


def test_required_milestone_tags_include_complete_history():
    required_tags = _module_required_tags()

    for tag in EXPECTED_MILESTONE_TAGS:
        assert tag in required_tags


def test_required_release_files_exist():
    required_files = getattr(
        release_check,
        "REQUIRED_FILES",
        [
            "README.md",
            "pyproject.toml",
            "omega_runtime/api.py",
            "omega_runtime/release_check.py",
            "scripts/release_check.py",
            "scripts/demo_evidence_pack.py",
        ],
    )

    for file_path in required_files:
        assert Path(file_path).exists(), f"Missing required file: {file_path}"


def test_required_release_directories_exist():
    required_directories = getattr(
        release_check,
        "REQUIRED_DIRECTORIES",
        [
            "omega_runtime",
            "omega_runtime/core",
            "scripts",
            "tests",
        ],
    )

    for directory_path in required_directories:
        assert Path(directory_path).is_dir(), f"Missing required directory: {directory_path}"


def test_release_check_accepts_current_repository_state():
    report = _run_release_check()

    assert report["accepted"] is True
    assert report["release_version"] == EXPECTED_RELEASE_VERSION
    assert report["checks_failed"] == 0
    assert report["checks_passed"] == report["checks_total"]
    assert "aggregate_hash" in report
    assert "checks" in report
    assert isinstance(report["checks"], list)


def test_release_check_writes_report_path():
    completed = subprocess.run(
        [sys.executable, "scripts/release_check.py", "--json"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr

    report = json.loads(completed.stdout)
    report_path = Path(report["report_path"])

    assert report["accepted"] is True
    assert report_path.exists()
    assert report_path.name == "release_check_report.json"
