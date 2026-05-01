from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.types import Action


def test_no_certificate_rejected():
    proxy = OmegaProxy()

    action = Action(
        run_id="test-run",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="test-nonce-001",
    )

    result = proxy.execute(action, None)

    assert result.accepted is False
    assert result.reason == "no certificate"
