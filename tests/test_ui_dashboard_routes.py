from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from omega_runtime.api import app


def _generate_demo_artifacts() -> None:
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


def test_dashboard_verify_system_routes_exist_and_accept_demo_artifacts():
    _generate_demo_artifacts()

    client = TestClient(app)

    payload = {
        "proof_bundle_path": "artifacts/proof_bundle_demo.json",
        "trace_path": "traces/replay-verifier-demo.jsonl",
    }

    for route in [
        "/verify/system",
        "/system/verify",
        "/runtime/verify",
        "/audit/system",
    ]:
        response = client.post(route, json=payload)

        assert response.status_code == 200

        data = response.json()

        assert data["accepted"] is True
        assert data["reason"] == "system verification passed"
        assert data["artifact_count"] == 2
        assert data["requested_proof_bundles"] == ["artifacts/proof_bundle_demo.json"]
        assert data["requested_traces"] == ["traces/replay-verifier-demo.jsonl"]


def test_dashboard_verify_system_route_rejects_missing_artifacts():
    client = TestClient(app)

    response = client.post("/verify/system", json={})

    assert response.status_code == 200

    data = response.json()

    assert data["accepted"] is False
    assert data["reason"] == "no artifacts supplied"
