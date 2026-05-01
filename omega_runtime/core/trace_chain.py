from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from omega_runtime.core.types import Action, Certificate, Receipt


TRACE_CHAIN_TYPE = "OMEGA_TRACE_CHAIN_V1"


def _to_plain(value: Any) -> Any:
    if is_dataclass(value):
        return _to_plain(asdict(value))

    if isinstance(value, dict):
        return {str(k): _to_plain(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [_to_plain(v) for v in value]

    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        _to_plain(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _without_integrity_fields(bundle: dict[str, Any]) -> dict[str, Any]:
    clean = dict(bundle)
    clean.pop("trace_hash", None)
    return clean


def compute_trace_step_hash(
    *,
    previous_step_hash: str | None,
    action_hash: str,
    certificate_hash: str,
    receipt_hash: str,
    run_id: str,
    step_index: int,
) -> str:
    return stable_hash(
        {
            "previous_step_hash": previous_step_hash,
            "action_hash": action_hash,
            "certificate_hash": certificate_hash,
            "receipt_hash": receipt_hash,
            "run_id": run_id,
            "step_index": step_index,
        }
    )


def build_trace_step(
    *,
    action: Action,
    certificate: Certificate,
    receipt: Receipt,
    previous_step_hash: str | None,
) -> dict[str, Any]:
    action_plain = _to_plain(action)
    certificate_plain = _to_plain(certificate)
    receipt_plain = _to_plain(receipt)

    action_hash = stable_hash(action_plain)
    certificate_hash = stable_hash(certificate_plain)
    receipt_hash = stable_hash(receipt_plain)

    step_hash = compute_trace_step_hash(
        previous_step_hash=previous_step_hash,
        action_hash=action_hash,
        certificate_hash=certificate_hash,
        receipt_hash=receipt_hash,
        run_id=action.run_id,
        step_index=action.step_index,
    )

    return {
        "step_type": "OMEGA_TRACE_STEP_V1",
        "run_id": action.run_id,
        "step_index": action.step_index,
        "previous_step_hash": previous_step_hash,
        "action": action_plain,
        "certificate": certificate_plain,
        "receipt": receipt_plain,
        "action_hash": action_hash,
        "certificate_hash": certificate_hash,
        "receipt_hash": receipt_hash,
        "step_hash": step_hash,
    }


def build_trace_chain(
    executions: list[tuple[Action, Certificate, Receipt]],
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    previous_step_hash: str | None = None

    for action, certificate, receipt in executions:
        step = build_trace_step(
            action=action,
            certificate=certificate,
            receipt=receipt,
            previous_step_hash=previous_step_hash,
        )
        steps.append(step)
        previous_step_hash = step["step_hash"]

    bundle = {
        "trace_chain_type": TRACE_CHAIN_TYPE,
        "step_count": len(steps),
        "steps": steps,
        "trace_root_hash": previous_step_hash,
    }
    bundle["trace_hash"] = stable_hash(_without_integrity_fields(bundle))
    return bundle


def write_trace_chain(
    *,
    path: str | Path,
    executions: list[tuple[Action, Certificate, Receipt]],
) -> dict[str, Any]:
    bundle = build_trace_chain(executions)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(bundle, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return bundle


def verify_trace_chain(path: str | Path) -> tuple[bool, str]:
    try:
        bundle = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"trace chain read error: {exc}"

    if bundle.get("trace_chain_type") != TRACE_CHAIN_TYPE:
        return False, "invalid trace chain type"

    expected_trace_hash = stable_hash(_without_integrity_fields(bundle))
    if bundle.get("trace_hash") != expected_trace_hash:
        return False, "trace_hash mismatch"

    steps = bundle.get("steps")
    if not isinstance(steps, list):
        return False, "trace steps missing"

    if bundle.get("step_count") != len(steps):
        return False, "trace step_count mismatch"

    previous_step_hash: str | None = None
    previous_step_index: int | None = None
    run_id: str | None = None

    for position, step in enumerate(steps):
        if step.get("step_type") != "OMEGA_TRACE_STEP_V1":
            return False, f"trace step {position} has invalid step_type"

        action = step.get("action")
        certificate = step.get("certificate")
        receipt = step.get("receipt")

        if not isinstance(action, dict):
            return False, f"trace step {position} action missing"

        if not isinstance(certificate, dict):
            return False, f"trace step {position} certificate missing"

        if not isinstance(receipt, dict):
            return False, f"trace step {position} receipt missing"

        action_hash = stable_hash(action)
        certificate_hash = stable_hash(certificate)
        receipt_hash = stable_hash(receipt)

        if step.get("action_hash") != action_hash:
            return False, "action_hash mismatch"

        if step.get("certificate_hash") != certificate_hash:
            return False, "certificate_hash mismatch"

        if step.get("receipt_hash") != receipt_hash:
            return False, "receipt_hash mismatch"

        if step.get("previous_step_hash") != previous_step_hash:
            return False, "trace chain link mismatch"

        step_run_id = step.get("run_id")
        step_index = step.get("step_index")

        if run_id is None:
            run_id = step_run_id
        elif step_run_id != run_id:
            return False, "trace run_id mismatch"

        if previous_step_index is not None and step_index != previous_step_index + 1:
            return False, "trace step ordering mismatch"

        if action.get("run_id") != step_run_id:
            return False, "action run_id mismatch"

        if action.get("step_index") != step_index:
            return False, "action step_index mismatch"

        if receipt.get("run_id") != step_run_id:
            return False, "receipt run_id mismatch"

        if receipt.get("step_index") != step_index:
            return False, "receipt step_index mismatch"

        if receipt.get("action_hash") != action_hash:
            return False, "receipt action_hash mismatch"

        payload = certificate.get("payload")
        if not isinstance(payload, dict):
            return False, "certificate payload missing"

        if payload.get("run_id") != step_run_id:
            return False, "certificate run_id mismatch"

        if payload.get("step_index") != step_index:
            return False, "certificate step_index mismatch"

        if payload.get("action_hash") != action_hash:
            return False, "certificate action_hash mismatch"

        expected_step_hash = compute_trace_step_hash(
            previous_step_hash=previous_step_hash,
            action_hash=action_hash,
            certificate_hash=certificate_hash,
            receipt_hash=receipt_hash,
            run_id=step_run_id,
            step_index=step_index,
        )

        if step.get("step_hash") != expected_step_hash:
            return False, "trace step_hash mismatch"

        previous_step_hash = expected_step_hash
        previous_step_index = step_index

    if bundle.get("trace_root_hash") != previous_step_hash:
        return False, "trace_root_hash mismatch"

    return True, "trace chain valid"
