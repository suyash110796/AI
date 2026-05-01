from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib import import_module
import json
from pathlib import Path
from typing import Any, Callable

from omega_runtime.core.canonical import sha256_hex


AUDITOR_VERSION = "OMEGA_AUDITOR_V1"


@dataclass(frozen=True)
class AuditItem:
    artifact_type: str
    path: str
    accepted: bool
    reason: str
    artifact_hash: str | None = None
    detail: dict[str, Any] | None = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def file_hash(path: str | Path) -> str:
    data = Path(path).read_bytes()
    return sha256_hex(data.decode("utf-8", errors="replace"))


def _normalize_verifier_result(result: Any) -> tuple[bool, str, dict[str, Any]]:
    """
    Accept verifier outputs in the shapes already used across this project:

    1. tuple[bool, str]
    2. tuple[bool, str, ...]
    3. dict with accepted/passed + reason
    4. dataclass/object with accepted/passed + reason
    """
    if isinstance(result, tuple):
        if len(result) < 2:
            return False, "verifier returned malformed tuple", {"raw": repr(result)}
        accepted = bool(result[0])
        reason = str(result[1])
        detail = {"raw": repr(result)}
        return accepted, reason, detail

    if isinstance(result, dict):
        if "accepted" in result:
            accepted = bool(result["accepted"])
        elif "passed" in result:
            accepted = bool(result["passed"])
        else:
            accepted = False

        reason = str(result.get("reason", "verifier returned no reason"))
        return accepted, reason, dict(result)

    accepted = getattr(result, "accepted", None)
    if accepted is None:
        accepted = getattr(result, "passed", None)

    reason = getattr(result, "reason", None)

    if accepted is not None:
        detail = {}
        try:
            detail = asdict(result)
        except Exception:
            detail = {"raw": repr(result)}
        return bool(accepted), str(reason or "verifier returned no reason"), detail

    return False, "verifier returned unsupported result type", {"raw": repr(result)}


def _load_callable(module_name: str, candidate_names: list[str]) -> Callable[[Path], Any] | None:
    try:
        module = import_module(module_name)
    except Exception:
        return None

    for name in candidate_names:
        fn = getattr(module, name, None)
        if callable(fn):
            return fn

    return None


def _verify_with_candidates(
    *,
    artifact_type: str,
    path: str | Path,
    module_name: str,
    candidate_names: list[str],
) -> AuditItem:
    p = Path(path)

    if not p.exists():
        return AuditItem(
            artifact_type=artifact_type,
            path=str(p),
            accepted=False,
            reason="artifact missing",
            artifact_hash=None,
            detail=None,
        )

    artifact_hash = file_hash(p)

    verifier = _load_callable(module_name, candidate_names)
    if verifier is None:
        return AuditItem(
            artifact_type=artifact_type,
            path=str(p),
            accepted=False,
            reason=f"verifier not found for {artifact_type}",
            artifact_hash=artifact_hash,
            detail={
                "module": module_name,
                "candidate_names": candidate_names,
            },
        )

    try:
        result = verifier(p)
    except Exception as exc:
        return AuditItem(
            artifact_type=artifact_type,
            path=str(p),
            accepted=False,
            reason=f"verifier raised: {exc}",
            artifact_hash=artifact_hash,
            detail={"exception_type": type(exc).__name__},
        )

    accepted, reason, detail = _normalize_verifier_result(result)

    return AuditItem(
        artifact_type=artifact_type,
        path=str(p),
        accepted=accepted,
        reason=reason,
        artifact_hash=artifact_hash,
        detail=detail,
    )


def audit_artifacts(
    *,
    proof_bundle: str | Path | None = None,
    episode_bundle: str | Path | None = None,
    trace: str | Path | None = None,
    final_report: str | Path | None = None,
) -> dict[str, Any]:
    """
    Run the offline auditor over any supplied runtime artifacts.

    The auditor is intentionally additive:
    - pass a proof bundle to verify a single certified tool execution
    - pass an episode bundle to verify a multi-step episode
    - pass a trace to verify replay/ledger integrity
    - pass a final report to verify/report final machine verdict integrity
    """
    items: list[AuditItem] = []

    if proof_bundle is not None:
        items.append(
            _verify_with_candidates(
                artifact_type="proof_bundle",
                path=proof_bundle,
                module_name="omega_runtime.core.proof_bundle",
                candidate_names=[
                    "verify_proof_bundle_json",
                    "verify_proof_bundle",
                ],
            )
        )

    if episode_bundle is not None:
        items.append(
            _verify_with_candidates(
                artifact_type="episode_bundle",
                path=episode_bundle,
                module_name="omega_runtime.core.episode_bundle",
                candidate_names=[
                    "verify_episode_bundle_json",
                    "verify_episode_bundle",
                ],
            )
        )

    if trace is not None:
        items.append(
            _verify_with_candidates(
                artifact_type="trace",
                path=trace,
                module_name="omega_runtime.core.replay_verifier",
                candidate_names=[
                    "verify_replay_json",
                    "verify_replay_ledger_json",
                    "verify_replay_verdict_json",
                    "verify_replay_ledger",
                    "verify_replay",
                    "verify_trace",
                    "verify_ledger",
                ],
            )
        )

    if final_report is not None:
        items.append(
            _verify_with_candidates(
                artifact_type="final_report",
                path=final_report,
                module_name="omega_runtime.core.final_verifier_report",
                candidate_names=[
                    "verify_final_report_json",
                    "verify_final_verifier_report_json",
                    "verify_final_report",
                    "verify_final_verifier_report",
                    "verify_report",
                ],
            )
        )

    accepted = bool(items) and all(item.accepted for item in items)

    if not items:
        reason = "no artifacts supplied"
    elif accepted:
        reason = "audit passed"
    else:
        failed = [item for item in items if not item.accepted]
        reason = failed[0].reason if failed else "audit failed"

    payload: dict[str, Any] = {
        "audit_type": AUDITOR_VERSION,
        "auditor_version": AUDITOR_VERSION,
        "generated_at": utc_now_iso(),
        "accepted": accepted,
        "reason": reason,
        "artifact_count": len(items),
        "items": [asdict(item) for item in items],
    }

    payload["aggregate_hash"] = sha256_hex(payload)

    return payload


def write_audit_report(
    *,
    path: str | Path,
    proof_bundle: str | Path | None = None,
    episode_bundle: str | Path | None = None,
    trace: str | Path | None = None,
    final_report: str | Path | None = None,
) -> dict[str, Any]:
    report = audit_artifacts(
        proof_bundle=proof_bundle,
        episode_bundle=episode_bundle,
        trace=trace,
        final_report=final_report,
    )

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return report
