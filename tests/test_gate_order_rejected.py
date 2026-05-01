
from omega_runtime.core.gates import I011_GATE_ORDER
from omega_runtime.core.state import ActionPhase
from omega_runtime.core.stateful_proxy import StatefulOmegaProxy


def test_gate_order_rejected():
    proxy = StatefulOmegaProxy(run_id="state-order")

    # Expected first phase is START.
    gate = proxy.context.advance(ActionPhase.PLAN)

    assert gate.passed is False
    assert gate.invariant == I011_GATE_ORDER
    assert "gate order violation" in gate.reason
