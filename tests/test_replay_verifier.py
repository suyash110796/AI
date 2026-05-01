from __future__ import annotations

import json
from pathlib import Path

from omega_runtime.core.actions import Action
from omega_runtime.core.ledger import reset_ledger
from omega_runtime.core.policy_manifest import DEFAULT_POLICY_PATH, write_default_policy_manifest
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.replay_verifier import result_to_dict, verify_replay_trace
from omega_runtime.core.verifier import issue_certificate


def test_replay_verifier_accepts_valid_trace(tmp_path):
    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello replay verifier test", encoding="utf-8")

    trace_path = tmp_path / "valid_trace.jsonl"
    reset_ledger(trace_path)

    action = Action(
        run_id="replay-verifier-valid",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="replay-verifier-valid-nonce",
    )

    ok, reason, certificate = issue_certificate(action)
    assert ok, reason
    assert certificate is not None

    result = OmegaProxy(ledger_path=trace_path).execute(action, certificate)
    assert result.accepted is True

    replay = verify_replay_trace(trace_path)

    assert replay.passed is True
    assert replay.reason == "offline replay verification passed"
    assert replay.entries_checked == 1
    assert replay.final_entry_hash is not None
    assert replay.violations == []

    payload = result_to_dict(replay)
    assert payload["accepted"] is True
    assert payload["passed"] is True
    assert payload["entries_checked"] == 1


def test_replay_verifier_rejects_tampered_trace(tmp_path):
    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello replay tamper test", encoding="utf-8")

    trace_path = tmp_path / "tampered_trace.jsonl"
    reset_ledger(trace_path)

    action = Action(
        run_id="replay-verifier-tamper",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="replay-verifier-tamper-nonce",
    )

    ok, reason, certificate = issue_certificate(action)
    assert ok, reason
    assert certificate is not None

    result = OmegaProxy(ledger_path=trace_path).execute(action, certificate)
    assert result.accepted is True

    lines = trace_path.read_text(encoding="utf-8").splitlines()
    assert lines

    entry = json.loads(lines[0])
    entry["reason"] = "malicious post-facto trace edit"
    trace_path.write_text(json.dumps(entry, sort_keys=True) + "\n", encoding="utf-8")

    replay = verify_replay_trace(trace_path)

    assert replay.passed is False
    assert replay.violations
    assert replay.violations[0].code == "TRACE_HASH_CHAIN_REJECTED"


def test_replay_verifier_rejects_empty_trace(tmp_path):
    trace_path = tmp_path / "empty.jsonl"
    trace_path.write_text("", encoding="utf-8")

    replay = verify_replay_trace(trace_path)

    assert replay.passed is False
    assert replay.violations
    assert replay.violations[0].code in {"TRACE_HASH_CHAIN_REJECTED", "EMPTY_TRACE"}
