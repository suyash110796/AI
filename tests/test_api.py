from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from omega_runtime.api import app
from omega_runtime.core.policy_manifest import DEFAULT_POLICY_PATH, write_default_policy_manifest


def test_api_health():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()

    assert payload["accepted"] is True
    assert payload["api_version"] == "OMEGA_RUNTIME_API_V1"
    assert payload["reason"] == "healthy"


def test_api_executes_action_and_exports_proof_bundle(tmp_path):
    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    sandbox = Path("sandbox")
    sandbox.mkdir(exist_ok=True)
    input_path = sandbox / "api_input.txt"
    input_path.write_text("hello from api", encoding="utf-8")

    proof_path = tmp_path / "api_proof_bundle.json"

    client = TestClient(app)

    response = client.post(
        "/v1/execute",
        json={
            "run_id": "api-test",
            "step_index": 1,
            "tool": "sandbox.read_file",
            "args": {"path": str(input_path).replace("\\", "/")},
            "nonce": "api-test-nonce",
            "proof_bundle_path": str(proof_path),
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["accepted"] is True
    assert payload["certificate_issued"] is True
    assert payload["output"] == "hello from api"
    assert payload["proof_bundle_verified"] is True
    assert payload["proof_bundle_verify_reason"] == "proof bundle valid"
    assert proof_path.exists()


def test_api_verifies_proof_bundle(tmp_path):
    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    sandbox = Path("sandbox")
    sandbox.mkdir(exist_ok=True)
    input_path = sandbox / "api_verify_input.txt"
    input_path.write_text("verify me", encoding="utf-8")

    proof_path = tmp_path / "api_verify_proof_bundle.json"

    client = TestClient(app)

    execute_response = client.post(
        "/v1/execute",
        json={
            "run_id": "api-verify-test",
            "step_index": 1,
            "tool": "sandbox.read_file",
            "args": {"path": str(input_path).replace("\\", "/")},
            "nonce": "api-verify-test-nonce",
            "proof_bundle_path": str(proof_path),
        },
    )

    assert execute_response.status_code == 200
    assert execute_response.json()["accepted"] is True

    verify_response = client.post(
        "/v1/verify/proof-bundle",
        json={"path": str(proof_path)},
    )

    assert verify_response.status_code == 200
    payload = verify_response.json()

    assert payload["accepted"] is True
    assert payload["reason"] == "proof bundle valid"
    assert payload["artifact_type"] == "proof_bundle"


def test_api_system_verifier_accepts_valid_proof_bundle(tmp_path):
    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    sandbox = Path("sandbox")
    sandbox.mkdir(exist_ok=True)
    input_path = sandbox / "api_system_input.txt"
    input_path.write_text("system verify me", encoding="utf-8")

    proof_path = tmp_path / "api_system_proof_bundle.json"

    client = TestClient(app)

    execute_response = client.post(
        "/v1/execute",
        json={
            "run_id": "api-system-test",
            "step_index": 1,
            "tool": "sandbox.read_file",
            "args": {"path": str(input_path).replace("\\", "/")},
            "nonce": "api-system-test-nonce",
            "proof_bundle_path": str(proof_path),
        },
    )

    assert execute_response.status_code == 200
    assert execute_response.json()["accepted"] is True

    system_response = client.post(
        "/v1/system/verify",
        json={
            "proof_bundles": [str(proof_path)],
            "traces": [],
        },
    )

    assert system_response.status_code == 200
    payload = system_response.json()

    assert payload["accepted"] is True
    assert payload["reason"] == "system verification passed"
    assert payload["artifact_count"] == 1
