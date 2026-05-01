from pathlib import Path
import json

from omega_runtime.core.actions import Action
from omega_runtime.core.policy_manifest import DEFAULT_POLICY_PATH, write_default_policy_manifest
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.verifier import issue_certificate
from omega_runtime.core.proof_bundle import write_proof_bundle, verify_proof_bundle


def test_proof_bundle_export_valid(tmp_path):
    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello proof bundle test", encoding="utf-8")

    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    action = Action(
        run_id="proof-bundle-test",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="proof-bundle-test-nonce",
    )

    ok, reason, certificate = issue_certificate(action)
    assert ok, reason
    assert certificate is not None

    result = OmegaProxy().execute(action, certificate)
    assert result.accepted is True

    bundle_path = tmp_path / "proof_bundle.json"

    bundle = write_proof_bundle(
        action=action,
        certificate=certificate,
        result=result,
        path=bundle_path,
    )

    assert bundle_path.exists()
    assert bundle["bundle_type"] == "OMEGA_PROOF_BUNDLE_V1"
    assert bundle["accepted"] is True
    assert bundle["receipt"] is not None
    assert bundle["counterexample"] is None
    assert bundle["verification_summary"]["action_hash_bound"] is True
    assert bundle["verification_summary"]["policy_hash_bound"] is True
    assert bundle["verification_summary"]["nonce_bound"] is True

    verified, verify_reason = verify_proof_bundle(bundle_path)
    assert verified is True, verify_reason


def test_proof_bundle_tamper_detected(tmp_path):
    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello proof bundle tamper", encoding="utf-8")

    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    action = Action(
        run_id="proof-bundle-tamper-test",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="proof-bundle-tamper-test-nonce",
    )

    ok, reason, certificate = issue_certificate(action)
    assert ok, reason
    assert certificate is not None

    result = OmegaProxy().execute(action, certificate)
    assert result.accepted is True

    bundle_path = tmp_path / "proof_bundle.json"
    write_proof_bundle(
        action=action,
        certificate=certificate,
        result=result,
        path=bundle_path,
    )

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["reason"] = "tampered reason"
    bundle_path.write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")

    verified, verify_reason = verify_proof_bundle(bundle_path)
    assert verified is False
    assert verify_reason == "bundle_hash mismatch"
