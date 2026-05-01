from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from omega_runtime.core.canonical import sha256_hex
from omega_runtime.core.certificates import TRUSTED_CERTIFICATE_KEY_ID


BUNDLE_TYPE = "OMEGA_EPISODE_BUNDLE_V1"


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)

    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}

    if isinstance(value, list):
        return [_plain(v) for v in value]

    if isinstance(value, tuple):
        return [_plain(v) for v in value]

    return value


def _hash_bundle_payload(bundle: dict[str, Any]) -> str:
    body = dict(bundle)
    body.pop("bundle_hash", None)
    return sha256_hex(body)


def _write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _normalize_step(step: dict[str, Any]) -> dict[str, Any]:
    action = _plain(step["action"])
    certificate = _plain(step["certificate"])
    receipt = _plain(step["receipt"])

    action_hash = sha256_hex(action)
    certificate_hash = sha256_hex(certificate)
    receipt_hash = sha256_hex(receipt)

    cert_payload = certificate.get("payload", {})
    receipt_status = receipt.get("status")

    return {
        "step_index": action.get("step_index"),
        "run_id": action.get("run_id"),
        "tool": action.get("tool"),
        "action": action,
        "certificate": certificate,
        "receipt": receipt,
        "action_hash": action_hash,
        "certificate_hash": certificate_hash,
        "receipt_hash": receipt_hash,
        "verification_summary": {
            "certificate_action_hash_bound": cert_payload.get("action_hash") == action_hash,
            "receipt_action_hash_bound": receipt.get("action_hash") == action_hash,
            "receipt_executed": receipt_status == "EXECUTED",
        },
    }


def write_episode_bundle(
    *,
    path: str | Path,
    run_id: str,
    final_output: Any,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized_steps = [_normalize_step(step) for step in steps]

    bundle = {
        "bundle_type": BUNDLE_TYPE,
        "run_id": run_id,
        "step_count": len(normalized_steps),
        "final_output": final_output,
        "final_output_hash": sha256_hex(final_output),
        "steps": normalized_steps,
        "verification_summary": {
            "all_certificates_bound": all(
                step["verification_summary"]["certificate_action_hash_bound"]
                for step in normalized_steps
            ),
            "all_receipts_bound": all(
                step["verification_summary"]["receipt_action_hash_bound"]
                for step in normalized_steps
            ),
            "all_receipts_executed": all(
                step["verification_summary"]["receipt_executed"]
                for step in normalized_steps
            ),
        },
    }

    bundle["bundle_hash"] = _hash_bundle_payload(bundle)
    _write_json(path, bundle)
    return bundle


def export_episode_bundle(
    *,
    path: str | Path,
    run_id: str,
    final_output: Any,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    return write_episode_bundle(
        path=path,
        run_id=run_id,
        final_output=final_output,
        steps=steps,
    )


def _verify_step(step: dict[str, Any]) -> tuple[bool, str]:
    action = step.get("action")
    certificate = step.get("certificate")
    receipt = step.get("receipt")

    if not isinstance(action, dict):
        return False, "episode action malformed"

    if not isinstance(certificate, dict):
        return False, "episode certificate malformed"

    if not isinstance(receipt, dict):
        return False, "episode receipt malformed"

    action_hash = sha256_hex(action)

    if step.get("action_hash") != action_hash:
        return False, "episode action hash mismatch"

    payload = certificate.get("payload")
    if not isinstance(payload, dict):
        return False, "episode certificate payload malformed"

    if certificate.get("key_id") != TRUSTED_CERTIFICATE_KEY_ID:
        return False, "wrong certificate key"

    if payload.get("action_hash") != action_hash:
        return False, "episode certificate action_hash mismatch"

    if payload.get("run_id") != action.get("run_id"):
        return False, "episode certificate run_id mismatch"

    if payload.get("step_index") != action.get("step_index"):
        return False, "episode certificate step_index mismatch"

    if payload.get("tool") != action.get("tool"):
        return False, "episode certificate tool mismatch"

    if payload.get("nonce") != action.get("nonce"):
        return False, "episode certificate nonce mismatch"

    if receipt.get("action_hash") != action_hash:
        return False, "episode receipt action_hash mismatch"

    if receipt.get("status") != "EXECUTED":
        return False, "episode receipt not executed"

    if receipt.get("run_id") != action.get("run_id"):
        return False, "episode receipt run_id mismatch"

    if receipt.get("step_index") != action.get("step_index"):
        return False, "episode receipt step_index mismatch"

    if receipt.get("tool") != action.get("tool"):
        return False, "episode receipt tool mismatch"

    return True, "episode step valid"


def verify_episode_bundle(path: str | Path) -> tuple[bool, str]:
    path = Path(path)

    try:
        bundle = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"episode bundle unreadable: {exc}"

    if not isinstance(bundle, dict):
        return False, "episode bundle malformed"

    if bundle.get("bundle_type") != BUNDLE_TYPE:
        return False, "episode bundle type mismatch"

    stored_hash = bundle.get("bundle_hash")
    actual_hash = _hash_bundle_payload(bundle)

    if stored_hash != actual_hash:
        return False, "episode bundle hash mismatch"

    steps = bundle.get("steps")
    if not isinstance(steps, list):
        return False, "episode steps malformed"

    if bundle.get("step_count") != len(steps):
        return False, "episode step_count mismatch"

    if bundle.get("final_output_hash") != sha256_hex(bundle.get("final_output")):
        return False, "episode final_output hash mismatch"

    for step in steps:
        ok, reason = _verify_step(step)
        if not ok:
            return False, reason

    return True, "episode bundle valid"


def verify_episode_bundle_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)

    try:
        bundle = json.loads(path.read_text(encoding="utf-8"))
        bundle_hash = bundle.get("bundle_hash") if isinstance(bundle, dict) else None
    except Exception:
        bundle_hash = None

    accepted, reason = verify_episode_bundle(path)

    return {
        "accepted": accepted,
        "reason": reason,
        "bundle_hash": bundle_hash,
    }
