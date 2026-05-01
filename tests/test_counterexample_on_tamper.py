from pathlib import Path

from omega_runtime.core.invariants import I003_ACTION_HASH_BINDING
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.types import Action
from omega_runtime.core.verifier import issue_certificate


def test_counterexample_on_tamper():
    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello", encoding="utf-8")

    proxy = OmegaProxy()

    original_action = Action(
        run_id="cx-tamper-test",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="cx-tamper-nonce",
    )

    ok, reason, cert = issue_certificate(original_action)
    assert ok, reason

    tampered_action = Action(
        run_id="cx-tamper-test",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/other.txt"},
        nonce="cx-tamper-nonce",
    )

    result = proxy.execute(tampered_action, cert)

    assert result.accepted is False
    assert result.counterexample is not None
    assert result.counterexample.failed_invariant == I003_ACTION_HASH_BINDING
    assert result.counterexample.observed == "action_hash mismatch"
    assert result.counterexample.decision == "REJECT"
