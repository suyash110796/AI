from pathlib import Path

from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.types import Action
from omega_runtime.core.verifier import issue_certificate


def test_no_counterexample_on_accept():
    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello", encoding="utf-8")

    proxy = OmegaProxy()

    action = Action(
        run_id="cx-accept-test",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="cx-accept-nonce",
    )

    ok, reason, cert = issue_certificate(action)
    assert ok, reason

    result = proxy.execute(action, cert)

    assert result.accepted is True
    assert result.counterexample is None
    assert result.receipt is not None
