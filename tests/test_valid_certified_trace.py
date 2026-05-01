from pathlib import Path

from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.types import Action
from omega_runtime.core.verifier import issue_certificate


def test_valid_certified_trace():
    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello omega", encoding="utf-8")

    proxy = OmegaProxy()

    action = Action(
        run_id="test-valid",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="test-valid-nonce-001",
    )

    ok, reason, cert = issue_certificate(action)
    assert ok is True
    assert cert is not None

    result = proxy.execute(action, cert)

    assert result.accepted is True
    assert result.output == "hello omega"
    assert result.receipt is not None
