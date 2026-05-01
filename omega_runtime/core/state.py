
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RuntimeState(str, Enum):
    INIT = "INIT"
    READY = "READY"
    PLANNING = "PLANNING"
    TOOL_PENDING = "TOOL_PENDING"
    TOOL_EXECUTED = "TOOL_EXECUTED"
    VERIFYING = "VERIFYING"
    TERMINAL_ACCEPT = "TERMINAL_ACCEPT"
    TERMINAL_REJECT = "TERMINAL_REJECT"


class ActionPhase(str, Enum):
    START = "START"
    PLAN = "PLAN"
    REQUEST_TOOL = "REQUEST_TOOL"
    EXECUTE_TOOL = "EXECUTE_TOOL"
    VERIFY = "VERIFY"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


TERMINAL_STATES = {
    RuntimeState.TERMINAL_ACCEPT,
    RuntimeState.TERMINAL_REJECT,
}


@dataclass(frozen=True)
class Transition:
    from_state: RuntimeState
    phase: ActionPhase
    to_state: RuntimeState
    rule_id: str
