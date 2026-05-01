from omega_runtime.core.types import Action
from omega_runtime.core.verifier import issue_certificate


def test_path_escape_rejected():
    action = Action(
        run_id="test-path-escape",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "../outside.txt"},
        nonce="test-path-escape-nonce-001",
    )

    ok, reason, cert = issue_certificate(action)

    assert ok is False
    assert cert is None
    assert "path escapes sandbox" in reason
