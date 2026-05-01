from __future__ import annotations

from omega_runtime.core.invariants import (
    I011_WRONG_CERTIFICATE_KEY,
    expected_for_invariant,
    invariant_from_reason,
)
from omega_runtime.core.types import Action, Counterexample


def _counterexample_invariant_from_reason(reason: str) -> str:
    """
    Map proxy rejection reasons to the correct failed invariant.

    This override exists because wrong certificate-key failures must be
    classified as I011 before the generic policy-admission fallback gets used.
    """
    normalized = reason.strip().lower()

    # Exact wrong-key reasons.
    if normalized in {
        "wrong certificate key",
        "wrong certificate key_id",
        "wrong certificate key id",
        "certificate key mismatch",
        "certificate key_id mismatch",
        "certificate key id mismatch",
        "untrusted certificate key",
    }:
        return I011_WRONG_CERTIFICATE_KEY

    # Parameterized wrong-key reasons, for example:
    # "wrong certificate key: attacker-key-id"
    # "wrong certificate key_id: attacker-key-id"
    # "untrusted certificate key: attacker-key-id"
    # "certificate key mismatch: attacker-key-id"
    if normalized.startswith(
        (
            "wrong certificate key",
            "wrong certificate key_id",
            "wrong certificate key id",
            "certificate key mismatch",
            "certificate key_id mismatch",
            "certificate key id mismatch",
            "untrusted certificate key",
        )
    ):
        return I011_WRONG_CERTIFICATE_KEY

    # Defensive catch for any key-id based certificate rejection.
    if (
    "certificate" in normalized
    and ("key_id" in normalized or "key id" in normalized or "key" in normalized)
    and (
        "wrong" in normalized
        or "mismatch" in normalized
        or "untrusted" in normalized
    )
    ):
        return I011_WRONG_CERTIFICATE_KEY

    return invariant_from_reason(reason)


def build_counterexample(action: Action, reason: str) -> Counterexample:
    invariant = _counterexample_invariant_from_reason(reason)

    return Counterexample(
        counterexample_id=f"cx-{action.run_id}-{action.step_index}",
        run_id=action.run_id,
        step_index=action.step_index,
        failed_invariant=invariant,
        expected=expected_for_invariant(invariant),
        observed=reason,
        decision="REJECT",
    )


def format_counterexample(counterexample: Counterexample) -> str:
    return (
        "COUNTEREXAMPLE:\n"
        f"counterexample_id = {counterexample.counterexample_id}\n"
        f"failed_invariant = {counterexample.failed_invariant}\n"
        f"expected = {counterexample.expected}\n"
        f"observed = {counterexample.observed}\n"
        f"decision = {counterexample.decision}"
    )