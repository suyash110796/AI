from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from omega_runtime.core.system_verifier import verify_runtime_system


def test_system_verifier_rejects_empty_input():
    report = verify_runtime_system()

    assert report["accepted"] is False
    assert report["reason"] == "no artifacts supplied"
    assert report["artifact_count"] == 0
    assert report["items"] == []
    assert report["aggregate_hash"] is not None


def test_system_verifier_accepts_demo_proof_bundle_and_trace():
    subprocess.run(
        [sys.executable, "scripts/demo_proof_bundle.py"],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=True,
    )

    subprocess.run(
        [sys.executable, "scripts/demo_replay_verifier.py"],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=True,
    )

    report = verify_runtime_system(
        proof_bundles=["artifacts/proof_bundle_demo.json"],
        traces=["traces/replay-verifier-demo.jsonl"],
    )

    assert report["accepted"] is True
    assert report["reason"] == "system verification passed"
    assert report["artifact_count"] == 2
    assert all(item["accepted"] is True for item in report["items"])


def test_system_verifier_cli_writes_report(tmp_path):
    subprocess.run(
        [sys.executable, "scripts/demo_proof_bundle.py"],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=True,
    )

    subprocess.run(
        [sys.executable, "scripts/demo_replay_verifier.py"],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=True,
    )

    out_path = tmp_path / "system_report.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/verify_runtime_system.py",
            "--proof-bundle",
            "artifacts/proof_bundle_demo.json",
            "--trace",
            "traces/replay-verifier-demo.jsonl",
            "--out",
            str(out_path),
            "--json",
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert out_path.exists()

    stdout_payload = json.loads(completed.stdout)
    file_payload = json.loads(out_path.read_text(encoding="utf-8"))

    assert stdout_payload["accepted"] is True
    assert file_payload["accepted"] is True
    assert file_payload["reason"] == "system verification passed"
    assert file_payload["artifact_count"] == 2
