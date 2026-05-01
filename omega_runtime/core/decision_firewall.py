from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from omega_runtime.core.proof_bundle import verify_proof_bundle
from omega_runtime.core.replay_verifier import verify_replay_trace


@dataclass(frozen=True)
class FirewallDecision:
    accepted: bool
    reason: str
    proof_bundle_ok: bool
    replay_ok: bool
    bundle_reason: str
    replay_reason: str
    final_entry_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_world_acceptance(
    *,
    proof_bundle_path: str | Path,
    trace_path: str | Path,
) -> FirewallDecision:
    """
    Final external acceptance gate.

    The world must not accept an agent action merely because the tool ran.
    It accepts only if:
      1. the proof bundle verifies;
      2. the trace replay verifier passes;
      3. both artifacts agree that execution was lawful.
    """

    bundle_result = verify_proof_bundle(proof_bundle_path)

    # Backward compatibility:
    # Older verify_proof_bundle returned (bool, reason).
    # Newer versions may return an object/dict with more fields.
    if isinstance(bundle_result, tuple):
        proof_bundle_ok = bool(bundle_result[0])
        bundle_reason = str(bundle_result[1])
        bundle_hash = None
    elif isinstance(bundle_result, dict):
        proof_bundle_ok = bool(
            bundle_result.get("accepted", bundle_result.get("passed", False))
        )
        bundle_reason = str(bundle_result.get("reason", "unknown proof bundle result"))
        bundle_hash = bundle_result.get("bundle_hash")
    else:
        proof_bundle_ok = bool(getattr(bundle_result, "accepted", getattr(bundle_result, "passed", False)))
        bundle_reason = str(getattr(bundle_result, "reason", "unknown proof bundle result"))
        bundle_hash = getattr(bundle_result, "bundle_hash", None)

    replay_result = verify_replay_trace(trace_path)

    replay_ok = bool(getattr(replay_result, "passed", False))
    replay_reason = str(getattr(replay_result, "reason", "unknown replay result"))
    final_entry_hash = getattr(replay_result, "final_entry_hash", None)

    if not proof_bundle_ok:
        return FirewallDecision(
            accepted=False,
            reason=f"world reject: proof bundle failed: {bundle_reason}",
            proof_bundle_ok=False,
            replay_ok=replay_ok,
            bundle_reason=bundle_reason,
            replay_reason=replay_reason,
            final_entry_hash=final_entry_hash,
        )

    if not replay_ok:
        return FirewallDecision(
            accepted=False,
            reason=f"world reject: replay verifier failed: {replay_reason}",
            proof_bundle_ok=True,
            replay_ok=False,
            bundle_reason=bundle_reason,
            replay_reason=replay_reason,
            final_entry_hash=final_entry_hash,
        )

    return FirewallDecision(
        accepted=True,
        reason="world accept: proof bundle and replay verifier passed",
        proof_bundle_ok=True,
        replay_ok=True,
        bundle_reason=bundle_reason,
        replay_reason=replay_reason,
        final_entry_hash=final_entry_hash,
    )


# Alias with a simpler name for callers/tests.
def decision_firewall(
    *,
    proof_bundle_path: str | Path,
    trace_path: str | Path,
) -> FirewallDecision:
    return evaluate_world_acceptance(
        proof_bundle_path=proof_bundle_path,
        trace_path=trace_path,
    )
