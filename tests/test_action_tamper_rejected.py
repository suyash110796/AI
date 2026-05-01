from pathlib import Path

from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.types import Action
from omega_runtime.core.verifier import issue_certificate


def test_action_tamper_rejected():
    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("safe", encoding="utf-8")
    Path("sandbox/evil.txt").write_text("evil", encoding="utf-8")

    proxy = OmegaProxy()

    original = Action(
        run_id="test-tamper",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="test-tamper-nonce-001",
    )

    ok, reason, cert = issue_certificate(original)
    assert ok is True
    assert cert is not None

    tampered = Action(
        run_id="test-tamper",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/evil.txt"},
        nonce="test-tamper-nonce-001",
    )

    result = proxy.execute(tampered, cert)

    assert result.accepted is False
    assert result.reason == "action_hash mismatch"
