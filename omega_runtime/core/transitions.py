
from __future__ import annotations

from omega_runtime.core.state import ActionPhase, RuntimeState, TERMINAL_STATES, Transition


LEGAL_TRANSITIONS: dict[tuple[RuntimeState, ActionPhase], Transition] = {
    (RuntimeState.INIT, ActionPhase.START): Transition(
        RuntimeState.INIT,
        ActionPhase.START,
        RuntimeState.READY,
        "mu.t00.init_to_ready_by_start",
    ),
    (RuntimeState.READY, ActionPhase.PLAN): Transition(
        RuntimeState.READY,
        ActionPhase.PLAN,
        RuntimeState.PLANNING,
        "mu.t01.ready_to_planning_by_plan",
    ),
    (RuntimeState.PLANNING, ActionPhase.REQUEST_TOOL): Transition(
        RuntimeState.PLANNING,
        ActionPhase.REQUEST_TOOL,
        RuntimeState.TOOL_PENDING,
        "mu.t02.planning_to_tool_pending_by_request_tool",
    ),
    (RuntimeState.TOOL_PENDING, ActionPhase.EXECUTE_TOOL): Transition(
        RuntimeState.TOOL_PENDING,
        ActionPhase.EXECUTE_TOOL,
        RuntimeState.TOOL_EXECUTED,
        "mu.t03.tool_pending_to_tool_executed_by_execute_tool",
    ),
    (RuntimeState.TOOL_EXECUTED, ActionPhase.VERIFY): Transition(
        RuntimeState.TOOL_EXECUTED,
        ActionPhase.VERIFY,
        RuntimeState.VERIFYING,
        "mu.t04.tool_executed_to_verifying_by_verify",
    ),
    (RuntimeState.VERIFYING, ActionPhase.ACCEPT): Transition(
        RuntimeState.VERIFYING,
        ActionPhase.ACCEPT,
        RuntimeState.TERMINAL_ACCEPT,
        "mu.t05.verifying_to_terminal_accept",
    ),
    (RuntimeState.VERIFYING, ActionPhase.REJECT): Transition(
        RuntimeState.VERIFYING,
        ActionPhase.REJECT,
        RuntimeState.TERMINAL_REJECT,
        "mu.t06.verifying_to_terminal_reject",
    ),
}


def is_terminal(state: RuntimeState) -> bool:
    return state in TERMINAL_STATES


def get_transition(from_state: RuntimeState, phase: ActionPhase) -> Transition | None:
    return LEGAL_TRANSITIONS.get((from_state, phase))


def is_legal_transition(from_state: RuntimeState, phase: ActionPhase) -> bool:
    return get_transition(from_state, phase) is not None
