
from pathlib import Path

from omega_runtime.core.certificates import issue_certificate_for_action
from omega_runtime.core.state import RuntimeState
from omega_runtime.core.stateful_proxy import StatefulOmegaProxy
from omega_runtime.core.types import Action


def test_valid_transition_sequence():
    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello", encoding="utf-8")

    proxy = StatefulOmegaProxy(run_id="state-valid")

    assert proxy.start().passed is True
    assert proxy.plan().passed is True
    assert proxy.request_tool().passed is True

    action = Action(
        run_id="state-valid",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="state-valid-nonce",
    )

    cert = issue_certificate_for_action(action)
    result = proxy.execute_tool(action, cert)

    assert result.accepted is True
    assert result.tool_executed is True
    assert result.counterexample is None
    assert proxy.context.state == RuntimeState.TERMINAL_ACCEPT
    assert len(proxy.context.transition_certificates) == 6
