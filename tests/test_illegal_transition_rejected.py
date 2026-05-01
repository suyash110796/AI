
from omega_runtime.core.gates import I010_ILLEGAL_TRANSITION
from omega_runtime.core.state import ActionPhase
from omega_runtime.core.stateful_proxy import StatefulOmegaProxy


def test_illegal_transition_rejected():
    proxy = StatefulOmegaProxy(run_id="state-illegal")

    # Disable strict order to test pure transition legality:
    # INIT cannot execute a tool directly.
    proxy.context.phase_order = [ActionPhase.EXECUTE_TOOL]

    gate = proxy.context.advance(ActionPhase.EXECUTE_TOOL)

    assert gate.passed is False
    assert gate.invariant == I010_ILLEGAL_TRANSITION
    assert "illegal transition" in gate.reason
