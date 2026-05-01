from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


TRUSTED_CERTIFICATE_KEY_ID = "omega-runtime-test-key-v1"
_CERTIFICATE_SIGNING_KEY = b"omega-runtime-certificate-signing-key-v1"


@dataclass(frozen=True)
class CertificatePayload:
    certificate_id: str
    run_id: str
    step_index: int
    tool: str
    action_hash: str
    policy_hash: str
    nonce: str
    issued_at: str


@dataclass(frozen=True)
class Certificate:
    payload: CertificatePayload
    signature: str
    key_id: str = TRUSTED_CERTIFICATE_KEY_ID
    signature_algorithm: str = "HMAC-SHA256"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _to_plain(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, dict):
        return {str(k): _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(v) for v in value]
    return value


def stable_json(value: Any) -> str:
    return json.dumps(
        _to_plain(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def _payload_signature(payload: CertificatePayload) -> str:
    """
    Canonical certificate signature.

    build_certificate() and verify_certificate() must call this exact function.
    Never sign the whole Certificate object, because signature/key_id fields would
    make verification unstable and would turn action-tamper into signature-tamper.
    """
    raw = stable_json(payload).encode("utf-8")
    digest = hmac.new(_CERTIFICATE_SIGNING_KEY, raw, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def build_certificate(payload: CertificatePayload) -> Certificate:
    return Certificate(
        payload=payload,
        signature=_payload_signature(payload),
        key_id=TRUSTED_CERTIFICATE_KEY_ID,
        signature_algorithm="HMAC-SHA256",
    )


def verify_certificate(cert: Certificate | None) -> tuple[bool, str]:
    if cert is None:
        return False, "no certificate"

    if getattr(cert, "key_id", None) != TRUSTED_CERTIFICATE_KEY_ID:
        return False, "wrong certificate key"

    if getattr(cert, "signature_algorithm", None) != "HMAC-SHA256":
        return False, "invalid signature"

    expected = _payload_signature(cert.payload)
    observed = getattr(cert, "signature", "")

    if not isinstance(observed, str):
        return False, "invalid signature"

    if not hmac.compare_digest(observed, expected):
        return False, "invalid signature"

    return True, "certificate valid"


def issue_certificate_for_action(action: Any) -> Certificate:
    from omega_runtime.core.policy import POLICY_HASH

    payload = CertificatePayload(
        certificate_id=f"cert-{action.run_id}-{action.step_index}",
        run_id=action.run_id,
        step_index=action.step_index,
        tool=action.tool,
        action_hash=sha256_hex(action),
        policy_hash=POLICY_HASH,
        nonce=action.nonce,
        issued_at=utc_now_iso(),
    )
    return build_certificate(payload)
