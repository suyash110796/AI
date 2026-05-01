from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from omega_runtime.core.canonical import sha256_hex


REPORT_TYPE = "OMEGA_FINAL_VERIFIER_REPORT_V1"


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return {k: _plain(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if isinstance(value, tuple):
        return [_plain(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str | Path, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _hash_report_body(report: dict[str, Any]) -> str:
    body = dict(report)
    body.pop("report_hash", None)
    return sha256_hex(body)


def _verify_proof_bundle_component(path: str | Path) -> dict[str, Any]:
    from omega_runtime.core.proof_bundle import verify_proof_bundle

    accepted, reason = verify_proof_bundle(path)
    data = _read_json(path)

    return {
        "component_type": "proof_bundle",
        "path": str(path),
        "accepted": bool(accepted),
        "reason": reason,
        "bundle_hash": data.get("bundle_hash"),
    }


def _verify_episode_bundle_component(path: str | Path) -> dict[str, Any]:
    from omega_runtime.core.episode_bundle import verify_episode_bundle_json

    verdict = verify_episode_bundle_json(path)

    return {
        "component_type": "episode_bundle",
        "path": str(path),
        "accepted": bool(verdict.get("accepted")),
        "reason": verdict.get("reason"),
        "bundle_hash": verdict.get("bundle_hash"),
        "step_count": verdict.get("step_count"),
    }


def _normalize_replay_component(replay_verdict: dict[str, Any]) -> dict[str, Any]:
    accepted = bool(
        replay_verdict.get("accepted", replay_verdict.get("passed", False))
    )

    return {
        "component_type": "replay_verifier",
        "accepted": accepted,
        "reason": replay_verdict.get("reason", "replay verifier verdict supplied"),
        "entries_checked": replay_verdict.get("entries_checked"),
        "final_entry_hash": replay_verdict.get("final_entry_hash"),
        "violations": replay_verdict.get("violations", []),
    }


def build_final_verifier_report(
    *,
    run_id: str,
    proof_bundle_path: str | Path | None = None,
    episode_bundle_path: str | Path | None = None,
    replay_verdict: dict[str, Any] | None = None,
    extra_checks: list[dict[str, Any]] | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    """
    Build the final machine-checkable verifier report.

    This report is the top-level artifact:
    - proof bundle validity
    - episode bundle validity
    - optional replay-verifier verdict
    - optional extra machine checks
    - one tamper-evident report_hash over the whole report body
    """

    components: list[dict[str, Any]] = []

    if proof_bundle_path is not None:
        components.append(_verify_proof_bundle_component(proof_bundle_path))

    if episode_bundle_path is not None:
        components.append(_verify_episode_bundle_component(episode_bundle_path))

    if replay_verdict is not None:
        components.append(_normalize_replay_component(_plain(replay_verdict)))

    for check in extra_checks or []:
        normalized = _plain(check)
        normalized.setdefault("component_type", "extra_check")
        normalized.setdefault("accepted", bool(normalized.get("passed", False)))
        normalized.setdefault("reason", "extra check supplied")
        components.append(normalized)

    accepted = all(bool(component.get("accepted")) for component in components)

    report: dict[str, Any] = {
        "report_type": REPORT_TYPE,
        "run_id": run_id,
        "accepted": accepted,
        "reason": "final verifier report valid" if accepted else "final verifier report rejected",
        "component_count": len(components),
        "components": components,
    }

    report["report_hash"] = _hash_report_body(report)

    if path is not None:
        _write_json(path, report)

    return report


def verify_final_verifier_report(path: str | Path) -> tuple[bool, str]:
    report = _read_json(path)

    if report.get("report_type") != REPORT_TYPE:
        return False, "invalid final verifier report type"

    expected_hash = report.get("report_hash")
    actual_hash = _hash_report_body(report)

    if expected_hash != actual_hash:
        return False, "final verifier report hash mismatch"

    components = report.get("components")
    if not isinstance(components, list):
        return False, "final verifier report components malformed"

    for component in components:
        if not isinstance(component, dict):
            return False, "final verifier report component malformed"
        if component.get("accepted") is not True:
            return False, str(component.get("reason", "component rejected"))

    if report.get("accepted") is not True:
        return False, str(report.get("reason", "final verifier report rejected"))

    return True, "final verifier report valid"


def verify_final_verifier_report_json(path: str | Path) -> dict[str, Any]:
    accepted, reason = verify_final_verifier_report(path)
    report = _read_json(path)

    return {
        "accepted": accepted,
        "reason": reason,
        "report_type": report.get("report_type"),
        "run_id": report.get("run_id"),
        "report_hash": report.get("report_hash"),
        "component_count": report.get("component_count"),
    }
