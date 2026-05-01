from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from omega_runtime.core.canonical import sha256_hex
from omega_runtime.core.certificates import verify_certificate
from omega_runtime.core.policy import POLICY_HASH
from omega_runtime.core.types import Action, Certificate, ProxyResult, Receipt


BUNDLE_TYPE = "OMEGA_PROOF_BUNDLE_V1"


def _plain(value: Any) -> Any:
    if value is None:
        return None

    if is_dataclass(value):
        return _plain(asdict(value))

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]

    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _plain(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _bundle_hash_payload(bundle: dict[str, Any]) -> dict[str, Any]:
    payload = dict(bundle)
    payload.pop("bundle_hash", None)
    return payload


def compute_proof_bundle_hash(bundle: dict[str, Any]) -> str:
    return sha256_hex(_canonical_json(_bundle_hash_payload(bundle)))


def _build_verification_summary(
    *,
    action: Action,
    certificate: Certificate,
    receipt: Receipt | None,
) -> dict[str, bool]:
    action_hash = sha256_hex(action)

    cert_ok, _cert_reason = verify_certificate(certificate)

    receipt_action_hash_bound = True
    if receipt is not None:
        receipt_action_hash_bound = receipt.action_hash == action_hash

    return {
        "certificate_signature_valid": cert_ok,
        "action_hash_bound": certificate.payload.action_hash == action_hash,
        "policy_hash_bound": certificate.payload.policy_hash == POLICY_HASH,
        "nonce_bound": certificate.payload.nonce == action.nonce,
        "tool_bound": certificate.payload.tool == action.tool,
        "receipt_action_hash_bound": receipt_action_hash_bound,
    }


def export_proof_bundle(
    *,
    path: str | Path,
    action: Action,
    certificate: Certificate,
    receipt: Receipt | None = None,
    result: ProxyResult | None = None,
) -> dict[str, Any]:
    """
    Export an offline-checkable proof bundle.

    Supports both call styles used by the project tests:

        export_proof_bundle(path=..., action=..., certificate=..., receipt=...)

    and:

        write_proof_bundle(path=..., action=..., certificate=..., result=...)
    """
    output_receipt = receipt
    accepted = True
    reason = "proxy accept"
    counterexample = None

    if result is not None:
        output_receipt = result.receipt
        accepted = result.accepted
        reason = result.reason
        counterexample = result.counterexample

    bundle: dict[str, Any] = {
        "bundle_type": BUNDLE_TYPE,
        "run_id": action.run_id,
        "step_index": action.step_index,
        "accepted": accepted,
        "reason": reason,
        "action": _plain(action),
        "certificate": _plain(certificate),
        "receipt": _plain(output_receipt),
        "counterexample": _plain(counterexample),
        "verification_summary": _build_verification_summary(
            action=action,
            certificate=certificate,
            receipt=output_receipt,
        ),
    }

    bundle["bundle_hash"] = compute_proof_bundle_hash(bundle)

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(bundle, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )

    return bundle


def write_proof_bundle(
    *,
    action: Action,
    certificate: Certificate,
    result: ProxyResult,
    path: str | Path,
) -> dict[str, Any]:
    return export_proof_bundle(
        path=path,
        action=action,
        certificate=certificate,
        result=result,
    )


def verify_proof_bundle(path: str | Path) -> tuple[bool, str]:
    bundle_path = Path(path)

    if not bundle_path.exists():
        return False, "proof bundle not found"

    try:
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"invalid proof bundle json: {exc}"

    if not isinstance(bundle, dict):
        return False, "invalid proof bundle"

    if bundle.get("bundle_type") != BUNDLE_TYPE:
        return False, "invalid proof bundle type"

    expected_hash = bundle.get("bundle_hash")
    if not isinstance(expected_hash, str) or not expected_hash:
        return False, "missing bundle_hash"

    actual_hash = compute_proof_bundle_hash(bundle)
    if actual_hash != expected_hash:
        return False, "bundle_hash mismatch"

    summary = bundle.get("verification_summary")
    if not isinstance(summary, dict):
        return False, "missing verification_summary"

    required_true_flags = (
        "certificate_signature_valid",
        "action_hash_bound",
        "policy_hash_bound",
        "nonce_bound",
        "tool_bound",
        "receipt_action_hash_bound",
    )

    for flag in required_true_flags:
        if summary.get(flag) is not True:
            return False, f"verification summary failed: {flag}"

    return True, "proof bundle valid"


# Backwards-compatible aliases.
write_bundle = write_proof_bundle
export_bundle = export_proof_bundle
verify_bundle = verify_proof_bundle
