from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from hashlib import sha256
from importlib import import_module
from pathlib import Path
from typing import Any


SYSTEM_VERIFIER_VERSION = "OMEGA_SYSTEM_VERIFIER_V1"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _sha256_hex(value: Any) -> str:
    if isinstance(value, (str, bytes, bytearray)):
        raw = value if isinstance(value, (bytes, bytearray)) else value.encode("utf-8")
    else:
        raw = _canonical_json(value).encode("utf-8")
    return sha256(raw).hexdigest()


def _file_hash(path: str | Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def _safe_detail_from_object(raw: Any) -> dict[str, Any]:
    if is_dataclass(raw):
        try:
            return asdict(raw)
        except Exception:
            pass

    detail: dict[str, Any] = {}

    for name in (
        "accepted",
        "passed",
        "reason",
        "entries_checked",
        "final_entry_hash",
        "violations",
        "bundle_hash",
        "aggregate_hash",
    ):
        if hasattr(raw, name):
            value = getattr(raw, name)
            try:
                json.dumps(value, default=str)
                detail[name] = value
            except TypeError:
                detail[name] = str(value)

    if not detail:
        detail["raw"] = repr(raw)

    return detail


def _normalize_verifier_result(raw: Any) -> tuple[bool, str, dict[str, Any]]:
    """
    Normalize every verifier shape currently used by the runtime.

    Supported forms:
    - tuple: (bool, reason)
    - dict: {"accepted": bool, "reason": "..."} or {"passed": bool, "reason": "..."}
    - bool
    - dataclass/object with .accepted or .passed and optional .reason

    This is the critical compatibility path for ReplayVerificationResult:
        ReplayVerificationResult(passed=True, reason="offline replay verification passed", ...)
    """
    if isinstance(raw, tuple):
        accepted = bool(raw[0]) if len(raw) >= 1 else False
        reason = str(raw[1]) if len(raw) >= 2 else ("accepted" if accepted else "rejected")
        return accepted, reason, {"raw": list(raw)}

    if isinstance(raw, dict):
        if "accepted" in raw:
            accepted = bool(raw["accepted"])
        elif "passed" in raw:
            accepted = bool(raw["passed"])
        else:
            accepted = False

        reason = str(raw.get("reason", "accepted" if accepted else "rejected"))
        return accepted, reason, dict(raw)

    if isinstance(raw, bool):
        return raw, "accepted" if raw else "rejected", {"raw": raw}

    if hasattr(raw, "accepted") or hasattr(raw, "passed"):
        accepted = bool(getattr(raw, "accepted", getattr(raw, "passed", False)))
        reason = str(getattr(raw, "reason", "accepted" if accepted else "rejected"))
        return accepted, reason, _safe_detail_from_object(raw)

    return False, f"unsupported verifier result type: {type(raw).__name__}", {"raw": repr(raw)}


def _call_verifier(module_name: str, function_names: list[str], path: str | Path) -> tuple[bool, str, dict[str, Any]]:
    module = import_module(module_name)

    for function_name in function_names:
        verifier = getattr(module, function_name, None)
        if verifier is None:
            continue

        raw = verifier(path)
        accepted, reason, detail = _normalize_verifier_result(raw)
        detail["verifier_module"] = module_name
        detail["verifier_function"] = function_name
        return accepted, reason, detail

    return (
        False,
        "verifier not found",
        {
            "module": module_name,
            "candidate_names": function_names,
        },
    )


def _verify_proof_bundle(path: str | Path) -> dict[str, Any]:
    accepted, reason, detail = _call_verifier(
        "omega_runtime.core.proof_bundle",
        [
            "verify_proof_bundle",
            "verify_proof_bundle_json",
            "verify_bundle",
        ],
        path,
    )

    return {
        "artifact_type": "proof_bundle",
        "path": str(Path(path)),
        "artifact_hash": _file_hash(path),
        "accepted": accepted,
        "reason": reason,
        "detail": detail,
    }


def _verify_trace(path: str | Path) -> dict[str, Any]:
    accepted, reason, detail = _call_verifier(
        "omega_runtime.core.replay_verifier",
        [
            "verify_replay_trace",
            "verify_replay_json",
            "verify_replay_ledger_json",
            "verify_replay_verdict_json",
            "verify_replay_ledger",
            "verify_replay",
            "verify_trace",
            "verify_ledger",
        ],
        path,
    )

    return {
        "artifact_type": "trace",
        "path": str(Path(path)),
        "artifact_hash": _file_hash(path),
        "accepted": accepted,
        "reason": reason,
        "detail": detail,
    }


def verify_runtime_system(
    *,
    proof_bundles: list[str | Path] | None = None,
    traces: list[str | Path] | None = None,
) -> dict[str, Any]:
    proof_bundles = list(proof_bundles or [])
    traces = list(traces or [])

    items: list[dict[str, Any]] = []

    for proof_bundle in proof_bundles:
        items.append(_verify_proof_bundle(proof_bundle))

    for trace in traces:
        items.append(_verify_trace(trace))

    if not items:
        accepted = False
        reason = "no artifacts supplied"
    else:
        accepted = all(bool(item["accepted"]) for item in items)
        reason = "system verification passed" if accepted else next(
            str(item["reason"]) for item in items if not item["accepted"]
        )

    report = {
        "verification_type": SYSTEM_VERIFIER_VERSION,
        "system_verifier_version": SYSTEM_VERIFIER_VERSION,
        "generated_at": _utc_now_iso(),
        "artifact_count": len(items),
        "accepted": accepted,
        "reason": reason,
        "items": items,
    }

    report["aggregate_hash"] = _sha256_hex(
        {
            "verification_type": report["verification_type"],
            "artifact_count": report["artifact_count"],
            "accepted": report["accepted"],
            "reason": report["reason"],
            "items": report["items"],
        }
    )

    return report


def write_runtime_system_report(
    *,
    path: str | Path,
    proof_bundles: list[str | Path] | None = None,
    traces: list[str | Path] | None = None,
) -> dict[str, Any]:
    report = verify_runtime_system(proof_bundles=proof_bundles, traces=traces)
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report
