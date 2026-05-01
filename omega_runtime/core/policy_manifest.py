from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any


DEFAULT_POLICY_PATH = Path("policy_manifest.json")

_POLICY_MANIFEST_SIGNING_KEY = b"omega-runtime-policy-manifest-key-v1"


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _signature_for_manifest_body(body: dict[str, Any]) -> str:
    return hmac.new(
        _POLICY_MANIFEST_SIGNING_KEY,
        _stable_json(body).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def build_default_policy_manifest() -> dict[str, Any]:
    from omega_runtime.core.policy import POLICY_HASH, POLICY_SPEC

    policy = {
        "allowed_tools": ["sandbox.read_file"],
        "sandbox_root": "sandbox",
    }

    body = {
        "manifest_id": "omega-runtime-policy-manifest",
        "version": 1,
        "policy_hash": POLICY_HASH,
        "policy": policy,
        "policy_spec": POLICY_SPEC,
        "policy_spec_hash": _sha256_hex(POLICY_SPEC),
        "signature_algorithm": "HMAC-SHA256",
    }

    return {
        **body,
        "signature": _signature_for_manifest_body(body),
    }


def write_default_policy_manifest(path: str | Path = DEFAULT_POLICY_PATH) -> Path:
    output_path = Path(path)
    manifest = build_default_policy_manifest()
    output_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    return output_path


def verify_policy_manifest(path: str | Path = DEFAULT_POLICY_PATH) -> tuple[bool, str, str | None]:
    from omega_runtime.core.policy import POLICY_HASH

    manifest_path = Path(path)

    if not manifest_path.exists():
        write_default_policy_manifest(manifest_path)

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return False, "policy manifest unreadable", None

    policy_hash = manifest.get("policy_hash")

    if policy_hash != POLICY_HASH:
        return False, "policy manifest hash mismatch", policy_hash

    policy = manifest.get("policy")
    if not isinstance(policy, dict):
        return False, "policy manifest hash mismatch", policy_hash

    allowed_tools = policy.get("allowed_tools")
    if allowed_tools != ["sandbox.read_file"]:
        return False, "policy manifest hash mismatch", policy_hash

    policy_spec = manifest.get("policy_spec")
    policy_spec_hash = manifest.get("policy_spec_hash")

    if not isinstance(policy_spec, dict):
        return False, "policy manifest hash mismatch", policy_hash

    if policy_spec_hash != _sha256_hex(policy_spec):
        return False, "policy manifest hash mismatch", policy_hash

    signature = manifest.get("signature")
    if not isinstance(signature, str):
        return False, "policy manifest signature mismatch", policy_hash

    body = dict(manifest)
    body.pop("signature", None)

    expected = _signature_for_manifest_body(body)

    if not hmac.compare_digest(signature, expected):
        return False, "policy manifest signature mismatch", policy_hash

    return True, "policy manifest valid", policy_hash


def ensure_default_policy_manifest(path: str | Path = DEFAULT_POLICY_PATH) -> Path:
    manifest_path = Path(path)

    if not manifest_path.exists():
        return write_default_policy_manifest(manifest_path)

    ok, reason, _policy_hash = verify_policy_manifest(manifest_path)

    if ok:
        return manifest_path

    if reason == "policy manifest hash mismatch":
        return write_default_policy_manifest(manifest_path)

    return manifest_path
