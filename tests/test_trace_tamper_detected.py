import json
from pathlib import Path

from omega_runtime.core.ledger import reset_ledger
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.replay import replay_trace
from omega_runtime.core.types import Action
from omega_runtime.core.verifier import issue_certificate


def test_trace_tamper_detected(tmp_path):
    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello", encoding="utf-8")

    trace_path = tmp_path / "trace.jsonl"
    reset_ledger(trace_path)
    proxy = OmegaProxy(ledger_path=trace_path)

    action = Action(
        run_id="tamper-test",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="tamper-test-nonce",
    )

    ok, reason, cert = issue_certificate(action)
    assert ok, reason

    result = proxy.execute(action, cert)
    assert result.accepted is True

    lines = trace_path.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[0])
    entry["reason"] = "malicious edit after the fact"
    trace_path.write_text(json.dumps(entry, sort_keys=True) + "\n", encoding="utf-8")

    replay = replay_trace(trace_path)
    assert replay.passed is False
    assert "entry_hash mismatch" in replay.reason
