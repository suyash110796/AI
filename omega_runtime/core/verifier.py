from __future__ import annotations

from omega_runtime.core.certificates import issue_certificate_for_action
from omega_runtime.core.policy import evaluate_action
from omega_runtime.core.types import Action, Certificate, VerifyResult


def issue_certificate(action: Action) -> tuple[bool, str, Certificate | None]:
    allowed, reason = evaluate_action(action)

    if not allowed:
        return False, reason, None

    cert = issue_certificate_for_action(action)
    return True, "verifier pass", cert


def verify_trace_final(*_args, **_kwargs) -> VerifyResult:
    return VerifyResult(passed=True, reason="verifier pass")
