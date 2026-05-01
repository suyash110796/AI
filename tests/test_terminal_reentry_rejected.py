
from pathlib import Path

from omega_runtime.core.certificates import issue_certificate_for_action
from omega_runtime.core.gates import I012_TERMINAL_REENTRY
from omega_runtime.core.state import ActionPhase
from omega_runtime.core.stateful_proxy import StatefulOmegaProxy
from omega_runtime.core.types import Action


def test_terminal_reentry_rejected():
    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello", encoding="utf-8")

    proxy = StatefulOmegaProxy(run_id="state-terminal")

    assert proxy.start().passed is True
    assert proxy.plan().passed is True
    assert proxy.request_tool().passed is True

    action = Action(
        run_id="state-terminal",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="state-terminal-nonce",
    )

    cert = issue_certificate_for_action(action)
    result = proxy.execute_tool(action, cert)
    assert result.accepted is True

    # Terminal state cannot reopen.
    gate = proxy.context.advance(ActionPhase.PLAN)

    assert gate.passed is False
    assert gate.invariant == I012_TERMINAL_REENTRY
    assert "terminal state cannot reopen" in gate.reason
