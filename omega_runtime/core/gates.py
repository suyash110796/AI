
from __future__ import annotations

from dataclasses import dataclass

from omega_runtime.core.state import ActionPhase, RuntimeState
from omega_runtime.core.transitions import get_transition, is_terminal


I010_ILLEGAL_TRANSITION = "I010_ILLEGAL_TRANSITION"
I011_GATE_ORDER = "I011_GATE_ORDER"
I012_TERMINAL_REENTRY = "I012_TERMINAL_REENTRY"


@dataclass(frozen=True)
class GateDecision:
    passed: bool
    invariant: str
    reason: str
    rule_id: str | None = None
    from_state: RuntimeState | None = None
    phase: ActionPhase | None = None
    to_state: RuntimeState | None = None


def evaluate_transition_gate(
    current_state: RuntimeState,
    requested_phase: ActionPhase,
    expected_phase: ActionPhase | None,
) -> GateDecision:
    if is_terminal(current_state):
        return GateDecision(
            passed=False,
            invariant=I012_TERMINAL_REENTRY,
            reason="terminal state cannot reopen",
            from_state=current_state,
            phase=requested_phase,
        )

    if expected_phase is not None and requested_phase != expected_phase:
        return GateDecision(
            passed=False,
            invariant=I011_GATE_ORDER,
            reason=f"gate order violation: expected {expected_phase.value}, got {requested_phase.value}",
            from_state=current_state,
            phase=requested_phase,
        )

    transition = get_transition(current_state, requested_phase)
    if transition is None:
        return GateDecision(
            passed=False,
            invariant=I010_ILLEGAL_TRANSITION,
            reason=f"illegal transition from {current_state.value} by {requested_phase.value}",
            from_state=current_state,
            phase=requested_phase,
        )

    return GateDecision(
        passed=True,
        invariant="PASS",
        reason="transition gate pass",
        rule_id=transition.rule_id,
        from_state=transition.from_state,
        phase=transition.phase,
        to_state=transition.to_state,
    )
