from __future__ import annotations

import json
from pathlib import Path

from omega_runtime.core.actions import Action
from omega_runtime.core.certificates import issue_certificate_for_action
from omega_runtime.core.decision_firewall import decision_firewall
from omega_runtime.core.ledger import reset_ledger
from omega_runtime.core.policy_manifest import DEFAULT_POLICY_PATH, write_default_policy_manifest
from omega_runtime.core.proof_bundle import export_proof_bundle
from omega_runtime.core.proxy import OmegaProxy


def _make_valid_firewall_artifacts(tmp_path: Path):
    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello firewall test", encoding="utf-8")

    trace_path = tmp_path / "trace.jsonl"
    bundle_path = tmp_path / "bundle.json"

    reset_ledger(trace_path)

    action = Action(
        run_id="firewall-test",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="firewall-test-nonce",
    )

    certificate = issue_certificate_for_action(action)

    proxy = OmegaProxy(ledger_path=trace_path)
    result = proxy.execute(action, certificate)

    assert result.accepted is True
    assert result.receipt is not None

    export_proof_bundle(
        path=bundle_path,
        action=action,
        certificate=certificate,
        receipt=result.receipt,
    )

    return trace_path, bundle_path


def test_decision_firewall_accepts_valid_artifacts(tmp_path):
    trace_path, bundle_path = _make_valid_firewall_artifacts(tmp_path)

    verdict = decision_firewall(
        proof_bundle_path=bundle_path,
        trace_path=trace_path,
    )

    assert verdict.accepted is True
    assert verdict.proof_bundle_ok is True
    assert verdict.replay_ok is True
    assert verdict.reason == "world accept: proof bundle and replay verifier passed"
    assert verdict.final_entry_hash is not None


def test_decision_firewall_rejects_tampered_proof_bundle(tmp_path):
    trace_path, bundle_path = _make_valid_firewall_artifacts(tmp_path)

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["reason"] = "tampered after export"
    bundle_path.write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")

    verdict = decision_firewall(
        proof_bundle_path=bundle_path,
        trace_path=trace_path,
    )

    assert verdict.accepted is False
    assert verdict.proof_bundle_ok is False
    assert verdict.replay_ok is True
    assert "proof bundle failed" in verdict.reason


def test_decision_firewall_rejects_tampered_trace(tmp_path):
    trace_path, bundle_path = _make_valid_firewall_artifacts(tmp_path)

    lines = trace_path.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[0])
    entry["reason"] = "tampered trace reason"
    trace_path.write_text(json.dumps(entry, sort_keys=True) + "\n", encoding="utf-8")

    verdict = decision_firewall(
        proof_bundle_path=bundle_path,
        trace_path=trace_path,
    )

    assert verdict.accepted is False
    assert verdict.proof_bundle_ok is True
    assert verdict.replay_ok is False
    assert "replay verifier failed" in verdict.reason
