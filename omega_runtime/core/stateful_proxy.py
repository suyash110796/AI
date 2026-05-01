
from __future__ import annotations

from dataclasses import dataclass

from omega_runtime.core.counterexample import Counterexample
from omega_runtime.core.gates import I010_ILLEGAL_TRANSITION, I011_GATE_ORDER, I012_TERMINAL_REENTRY
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.run_context import RunContext
from omega_runtime.core.state import ActionPhase


@dataclass(frozen=True)
class StatefulProxyResult:
    accepted: bool
    reason: str
    tool_executed: bool
    inner_result: object | None = None
    counterexample: Counterexample | None = None


def _transition_counterexample(run_id: str, invariant: str, reason: str) -> Counterexample:
    return Counterexample(
        counterexample_id=f"cx-{run_id}-transition",
        failed_invariant=invariant,
        expected="runtime transition must follow legal mu gate order before execution",
        observed=reason,
        decision="REJECT",
    )


class StatefulOmegaProxy:
    """
    v0.4 wrapper.

    This forces a lawful runtime phase sequence before the existing OmegaProxy
    is allowed to execute the real tool action.

    Sequence:
        INIT -> READY -> PLANNING -> TOOL_PENDING -> TOOL_EXECUTED -> VERIFYING -> TERMINAL_ACCEPT

    The actual tool is executed only at EXECUTE_TOOL.
    """

    def __init__(self, run_id: str, inner: OmegaProxy | None = None):
        self.context = RunContext(run_id=run_id)
        self.inner = inner or OmegaProxy()

    def start(self):
        return self.context.advance(ActionPhase.START)

    def plan(self):
        return self.context.advance(ActionPhase.PLAN)

    def request_tool(self):
        return self.context.advance(ActionPhase.REQUEST_TOOL)

    def verify(self):
        return self.context.advance(ActionPhase.VERIFY)

    def accept(self):
        return self.context.advance(ActionPhase.ACCEPT)

    def reject(self):
        return self.context.reject()

    def execute_tool(self, action, certificate) -> StatefulProxyResult:
        gate = self.context.advance(ActionPhase.EXECUTE_TOOL)
        if not gate.passed:
            return StatefulProxyResult(
                accepted=False,
                reason=gate.reason,
                tool_executed=False,
                counterexample=_transition_counterexample(
                    self.context.run_id,
                    gate.invariant,
                    gate.reason,
                ),
            )

        inner_result = self.inner.execute(action, certificate)

        if not getattr(inner_result, "accepted", False):
            self.reject()
            return StatefulProxyResult(
                accepted=False,
                reason=getattr(inner_result, "reason", "inner proxy rejected"),
                tool_executed=getattr(inner_result, "tool_executed", False),
                inner_result=inner_result,
                counterexample=getattr(inner_result, "counterexample", None),
            )

        verify_gate = self.verify()
        if not verify_gate.passed:
            return StatefulProxyResult(
                accepted=False,
                reason=verify_gate.reason,
                tool_executed=True,
                inner_result=inner_result,
                counterexample=_transition_counterexample(
                    self.context.run_id,
                    verify_gate.invariant,
                    verify_gate.reason,
                ),
            )

        accept_gate = self.accept()
        if not accept_gate.passed:
            return StatefulProxyResult(
                accepted=False,
                reason=accept_gate.reason,
                tool_executed=True,
                inner_result=inner_result,
                counterexample=_transition_counterexample(
                    self.context.run_id,
                    accept_gate.invariant,
                    accept_gate.reason,
                ),
            )

        return StatefulProxyResult(
            accepted=True,
            reason="stateful proxy accept",
            tool_executed=getattr(inner_result, "tool_executed", True),
            inner_result=inner_result,
            counterexample=None,
        )
