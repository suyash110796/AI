from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

RELEASE_CHECK_VERSION = "OMEGA_RELEASE_CHECK_V1"
RELEASE_VERSION = "1.3.0"

REQUIRED_FILES = [
    "README.md",
    "pyproject.toml",
    "omega_runtime/api.py",
    "omega_runtime/cli.py",
    "omega_runtime/release_check.py",
    "scripts/release_check.py",
    "scripts/demo_evidence_pack.py",
]

REQUIRED_DIRECTORIES = [
    "omega_runtime",
    "omega_runtime/core",
    "scripts",
    "tests",
]

MILESTONE_TAGS = [
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
    "v1.1.0-openai-live-adapter",
    "v1.2.0-cli-consolidation",
    "v1.0.0",
]

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def _hash_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(payload.encode("utf-8")).hexdigest()

def _run_git(args: list[str], root: Path) -> tuple[bool, str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

    output = completed.stdout.strip()

    if completed.returncode != 0:
        output = completed.stderr.strip() or output

    return completed.returncode == 0, output

def _check(name: str, accepted: bool, reason: str, detail: Any = None) -> dict[str, Any]:
    return {
        "name": name,
        "accepted": bool(accepted),
        "reason": reason,
        "detail": detail,
    }

def _parse_pyproject_version(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith("version"):
            parts = stripped.split("=", 1)

            if len(parts) == 2:
                return parts[1].strip().strip('"').strip("'")

    return None

def run_release_check(root: str | Path = ".") -> dict[str, Any]:
    root_path = Path(root).resolve()
    checks: list[dict[str, Any]] = []

    checks.append(
        _check(
            "project_root",
            (root_path / "pyproject.toml").exists() and (root_path / "omega_runtime").exists(),
            "project root detected" if (root_path / "pyproject.toml").exists() else "pyproject.toml missing",
            {"root": str(root_path)},
        )
    )

    missing_files = [
        path for path in REQUIRED_FILES
        if not (root_path / path).exists()
    ]

    checks.append(
        _check(
            "required_files",
            not missing_files,
            "all required files present" if not missing_files else "required files missing",
            {
                "required_files": REQUIRED_FILES,
                "missing_files": missing_files,
            },
        )
    )

    missing_directories = [
        path for path in REQUIRED_DIRECTORIES
        if not (root_path / path).is_dir()
    ]

    checks.append(
        _check(
            "required_directories",
            not missing_directories,
            "all required directories present" if not missing_directories else "required directories missing",
            {
                "required_directories": REQUIRED_DIRECTORIES,
                "missing_directories": missing_directories,
            },
        )
    )

    pyproject_path = root_path / "pyproject.toml"
    pyproject_text = pyproject_path.read_text(encoding="utf-8") if pyproject_path.exists() else ""
    found_version = _parse_pyproject_version(pyproject_text)

    checks.append(
        _check(
            "package_version",
            found_version == RELEASE_VERSION,
            "package version matches release version" if found_version == RELEASE_VERSION else "package version mismatch",
            {
                "expected": RELEASE_VERSION,
                "found": found_version,
            },
        )
    )

    ok_tags, raw_tags = _run_git(["tag"], root_path)
    tags = set(raw_tags.splitlines()) if ok_tags else set()
    missing_tags = [tag for tag in MILESTONE_TAGS if tag not in tags]

    checks.append(
        _check(
            "milestone_tags",
            ok_tags and not missing_tags,
            "all milestone tags present" if ok_tags and not missing_tags else "milestone tags missing",
            {
                "required_tags": MILESTONE_TAGS,
                "missing_tags": missing_tags,
                "git_available": ok_tags,
            },
        )
    )

    ok_head, head = _run_git(["rev-parse", "--short", "HEAD"], root_path)
    ok_branch, branch = _run_git(["branch", "--show-current"], root_path)
    ok_status, status = _run_git(["status", "--porcelain"], root_path)

    test_files = sorted(
        str(path.relative_to(root_path))
        for path in (root_path / "tests").glob("test_*.py")
    )

    checks.append(
        _check(
            "test_suite_present",
            len(test_files) > 0,
            "test suite present" if test_files else "no test files found",
            {
                "test_file_count": len(test_files),
                "test_files": test_files,
            },
        )
    )

    scripts = [
        "scripts/demo_proof_bundle.py",
        "scripts/demo_replay_verifier.py",
        "scripts/demo_failure_lab.py",
        "scripts/demo_evidence_pack.py",
        "scripts/release_check.py",
    ]

    missing_scripts = [
        path for path in scripts
        if not (root_path / path).exists()
    ]

    checks.append(
        _check(
            "release_scripts",
            not missing_scripts,
            "release scripts present" if not missing_scripts else "release scripts missing",
            {
                "required_scripts": scripts,
                "missing_scripts": missing_scripts,
            },
        )
    )

    accepted = all(item["accepted"] for item in checks)
    checks_passed = sum(1 for item in checks if item["accepted"])
    checks_failed = len(checks) - checks_passed

    report: dict[str, Any] = {
        "accepted": accepted,
        "reason": "release check passed" if accepted else "release check failed",
        "release_check_version": RELEASE_CHECK_VERSION,
        "release_version": RELEASE_VERSION,
        "generated_at": _utc_now(),
        "checks_total": len(checks),
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
        "checks": checks,
        "required_files": REQUIRED_FILES,
        "required_directories": REQUIRED_DIRECTORIES,
        "milestone_tags": MILESTONE_TAGS,
        "git": {
            "head": head if ok_head else None,
            "branch": branch if ok_branch else None,
            "working_tree_clean": ok_status and status == "",
            "status_porcelain": status if ok_status else None,
        },
    }

    report["aggregate_hash"] = _hash_json(
        {
            "release_check_version": RELEASE_CHECK_VERSION,
            "release_version": RELEASE_VERSION,
            "checks": checks,
            "git_head": report["git"]["head"],
        }
    )

    return report

def write_release_report(
    out_path: str | Path = "artifacts/release/release_check_report.json",
    root: str | Path = ".",
) -> dict[str, Any]:
    report = run_release_check(root=root)

    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )

    report["report_path"] = str(path)
    return report
