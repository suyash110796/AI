from __future__ import annotations

import tomllib
from pathlib import Path


def test_pyproject_declares_console_entrypoints():
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    scripts = data["project"]["scripts"]

    assert scripts["omega-verify-proof"] == "omega_runtime.cli:verify_proof_main"
    assert scripts["omega-verify-trace"] == "omega_runtime.cli:verify_trace_main"
    assert scripts["omega-verify-episode"] == "omega_runtime.cli:verify_episode_main"
    assert scripts["omega-audit"] == "omega_runtime.cli:audit_main"
    assert scripts["omega-system-verify"] == "omega_runtime.cli:system_verify_main"


def test_cli_entrypoints_are_importable():
    from omega_runtime.cli import (
        audit_main,
        system_verify_main,
        verify_episode_main,
        verify_proof_main,
        verify_trace_main,
    )

    assert callable(verify_proof_main)
    assert callable(verify_trace_main)
    assert callable(verify_episode_main)
    assert callable(audit_main)
    assert callable(system_verify_main)
