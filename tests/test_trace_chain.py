from __future__ import annotations

import json
from pathlib import Path

from omega_runtime.core.actions import Action
from omega_runtime.core.policy_manifest import DEFAULT_POLICY_PATH, write_default_policy_manifest
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.trace_chain import verify_trace_chain, write_trace_chain
from omega_runtime.core.verifier import issue_certificate


def _accepted_execution(run_id: str, step_index: int, nonce: str):
    action = Action(
        run_id=run_id,
        step_index=step_index,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce=nonce,
    )

    ok, reason, certificate = issue_certificate(action)
    assert ok, reason
    assert certificate is not None

    result = OmegaProxy().execute(action, certificate)
    assert result.accepted is True
    assert result.receipt is not None

    return action, certificate, result.receipt


def test_trace_chain_valid(tmp_path):
    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello trace chain test", encoding="utf-8")

    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    executions = [
        _accepted_execution("trace-chain-test", 1, "trace-chain-test-nonce-001"),
        _accepted_execution("trace-chain-test", 2, "trace-chain-test-nonce-002"),
    ]

    chain_path = tmp_path / "trace_chain.json"
    bundle = write_trace_chain(path=chain_path, executions=executions)

    assert chain_path.exists()
    assert bundle["trace_chain_type"] == "OMEGA_TRACE_CHAIN_V1"
    assert bundle["step_count"] == 2
    assert bundle["trace_root_hash"] is not None
    assert bundle["trace_hash"] is not None

    verified, reason = verify_trace_chain(chain_path)
    assert verified is True
    assert reason == "trace chain valid"


def test_trace_chain_tamper_detected(tmp_path):
    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello trace chain tamper", encoding="utf-8")

    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    executions = [
        _accepted_execution("trace-chain-tamper", 1, "trace-chain-tamper-nonce-001"),
        _accepted_execution("trace-chain-tamper", 2, "trace-chain-tamper-nonce-002"),
    ]

    chain_path = tmp_path / "trace_chain.json"
    write_trace_chain(path=chain_path, executions=executions)

    data = json.loads(chain_path.read_text(encoding="utf-8"))
    data["steps"][0]["action"]["args"]["path"] = "sandbox/evil.txt"
    chain_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    verified, reason = verify_trace_chain(chain_path)
    assert verified is False
    assert reason in {
        "trace_hash mismatch",
        "action_hash mismatch",
        "certificate action_hash mismatch",
        "receipt action_hash mismatch",
    }


def test_trace_chain_ordering_rejected(tmp_path):
    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello trace chain ordering", encoding="utf-8")

    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    executions = [
        _accepted_execution("trace-chain-order", 1, "trace-chain-order-nonce-001"),
        _accepted_execution("trace-chain-order", 3, "trace-chain-order-nonce-003"),
    ]

    chain_path = tmp_path / "trace_chain.json"
    write_trace_chain(path=chain_path, executions=executions)

    verified, reason = verify_trace_chain(chain_path)
    assert verified is False
    assert reason == "trace step ordering mismatch"
