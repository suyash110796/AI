from pathlib import Path

from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.types import Action
from omega_runtime.core.verifier import issue_certificate


def test_replay_rejected():
    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello replay", encoding="utf-8")

    proxy = OmegaProxy()

    action = Action(
        run_id="test-replay",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="test-replay-nonce-001",
    )

    ok, reason, cert = issue_certificate(action)
    assert ok is True
    assert cert is not None

    first = proxy.execute(action, cert)
    second = proxy.execute(action, cert)

    assert first.accepted is True
    assert second.accepted is False
    assert second.reason == "replay rejected: nonce already used"
