
from __future__ import annotations

from dataclasses import dataclass, field

from omega_runtime.core.gates import GateDecision, evaluate_transition_gate
from omega_runtime.core.state import ActionPhase, RuntimeState


DEFAULT_PHASE_ORDER = [
    ActionPhase.START,
    ActionPhase.PLAN,
    ActionPhase.REQUEST_TOOL,
    ActionPhase.EXECUTE_TOOL,
    ActionPhase.VERIFY,
    ActionPhase.ACCEPT,
]


@dataclass
class TransitionCertificate:
    run_id: str
    step_index: int
    rule_id: str
    from_state: str
    phase: str
    to_state: str
    decision: str = "ALLOW"


@dataclass
class RunContext:
    run_id: str
    state: RuntimeState = RuntimeState.INIT
    phase_order: list[ActionPhase] = field(default_factory=lambda: list(DEFAULT_PHASE_ORDER))
    cursor: int = 0
    transition_certificates: list[TransitionCertificate] = field(default_factory=list)
    last_failure: GateDecision | None = None

    def expected_phase(self) -> ActionPhase | None:
        if self.cursor >= len(self.phase_order):
            return None
        return self.phase_order[self.cursor]

    def advance(self, phase: ActionPhase) -> GateDecision:
        decision = evaluate_transition_gate(
            current_state=self.state,
            requested_phase=phase,
            expected_phase=self.expected_phase(),
        )

        if not decision.passed:
            self.last_failure = decision
            return decision

        assert decision.rule_id is not None
        assert decision.to_state is not None
        assert decision.from_state is not None
        assert decision.phase is not None

        cert = TransitionCertificate(
            run_id=self.run_id,
            step_index=len(self.transition_certificates) + 1,
            rule_id=decision.rule_id,
            from_state=decision.from_state.value,
            phase=decision.phase.value,
            to_state=decision.to_state.value,
        )
        self.transition_certificates.append(cert)
        self.state = decision.to_state
        self.cursor += 1
        self.last_failure = None
        return decision

    def reject(self) -> GateDecision:
        # Switch expected final phase from ACCEPT to REJECT if currently verifying.
        if self.expected_phase() == ActionPhase.ACCEPT:
            self.phase_order[self.cursor] = ActionPhase.REJECT
        return self.advance(ActionPhase.REJECT)
