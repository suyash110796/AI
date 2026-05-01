from __future__ import annotations

# Omega Runtime invariant identifiers.
#
# These constants are imported directly by tests and used by the proxy,
# certificate layer, counterexample builder, and policy manifest checks.
# Keep the string values stable: they are part of the externally visible
# certificate/counterexample contract.

I001_CERTIFICATE_REQUIRED = "I001_CERTIFICATE_REQUIRED"
I002_CERTIFICATE_SIGNATURE = "I002_CERTIFICATE_SIGNATURE"
I003_ACTION_HASH_BINDING = "I003_ACTION_HASH_BINDING"
I004_POLICY_HASH_BINDING = "I004_POLICY_HASH_BINDING"
I005_NONCE_BINDING = "I005_NONCE_BINDING"
I006_REPLAY_PROTECTION = "I006_REPLAY_PROTECTION"
I007_POLICY_ADMISSION = "I007_POLICY_ADMISSION"
I008_TOOL_EXECUTION_BOUNDARY = "I008_TOOL_EXECUTION_BOUNDARY"
I009_POLICY_MANIFEST_INTEGRITY = "I009_POLICY_MANIFEST_INTEGRITY"
I010_CERTIFICATE_SIGNATURE_TAMPER = "I010_CERTIFICATE_SIGNATURE_TAMPER"
I011_WRONG_CERTIFICATE_KEY = "I011_WRONG_CERTIFICATE_KEY"
I012_TRACE_CHAIN_BINDING = "I012_TRACE_CHAIN_BINDING"
I013_TRACE_STEP_ORDERING = "I013_TRACE_STEP_ORDERING"
I014_RECEIPT_CHAIN_BINDING = "I014_RECEIPT_CHAIN_BINDING"


def invariant_from_reason(reason: str) -> str:
    """
    Convert a proxy/certificate rejection reason into the invariant that failed.

    Ordering matters:
    - key-id failures must be classified before generic signature failures
    - action/policy binding failures must be classified before policy admission
    """
    r = (reason or "").lower()

    if "no certificate" in r:
        return I001_CERTIFICATE_REQUIRED

    if (
        "wrong certificate key" in r
        or "wrong key" in r
        or "untrusted certificate key" in r
        or "trusted certificate key id" in r
        or "key_id mismatch" in r
        or "key id mismatch" in r
        or "certificate key_id" in r
    ):
        return I011_WRONG_CERTIFICATE_KEY

    if "action_hash mismatch" in r or "action hash mismatch" in r:
        return I003_ACTION_HASH_BINDING

    if "policy_hash mismatch" in r or "policy hash mismatch" in r:
        return I004_POLICY_HASH_BINDING

    if "nonce mismatch" in r:
        return I005_NONCE_BINDING

    if "replay" in r or "nonce already used" in r:
        return I007_POLICY_ADMISSION

    if (
        "policy manifest signature" in r
        or "manifest signature" in r
        or "policy manifest hash mismatch" in r
        or "policy manifest missing" in r
        or "policy manifest invalid" in r
        or "manifest hash mismatch" in r
    ):
        return I009_POLICY_MANIFEST_INTEGRITY

    if (
        "invalid signature" in r
        or "signature mismatch" in r
        or "signature tamper" in r
        or "certificate signature" in r
    ):
        return I010_CERTIFICATE_SIGNATURE_TAMPER

    if "trace chain" in r or "previous certificate" in r:
        return I012_TRACE_CHAIN_BINDING

    if "step ordering" in r or "advance by exactly one" in r:
        return I013_TRACE_STEP_ORDERING

    if "receipt chain" in r or "previous receipt" in r:
        return I014_RECEIPT_CHAIN_BINDING

    if (
        "unknown tool" in r
        or "tool error" in r
        or "forbidden" in r
        or "outside sandbox" in r
        or "path escape" in r
        or "not allowed" in r
        or "policy" in r
    ):
        return I007_POLICY_ADMISSION

    return I007_POLICY_ADMISSION


def expected_for_invariant(invariant: str) -> str:
    expectations = {
        I001_CERTIFICATE_REQUIRED: "A certificate must be supplied before tool execution",
        I002_CERTIFICATE_SIGNATURE: "Certificate signature must verify before execution",
        I003_ACTION_HASH_BINDING: "Certificate action_hash must match the submitted action",
        I004_POLICY_HASH_BINDING: "Certificate policy_hash must match the active policy hash",
        I005_NONCE_BINDING: "Certificate nonce must match the submitted action nonce",
        I006_REPLAY_PROTECTION: "A certificate nonce must not be reused",
        I007_POLICY_ADMISSION: "Action must be admitted by the active policy before execution",
        I008_TOOL_EXECUTION_BOUNDARY: "Only admitted tools may execute through the proxy boundary",
        I009_POLICY_MANIFEST_INTEGRITY: "Signed policy manifest hash and signature must verify before action execution",
        I010_CERTIFICATE_SIGNATURE_TAMPER: "Ed25519 signature must verify against trusted certificate public key",
        I011_WRONG_CERTIFICATE_KEY: "Certificate key_id must match the trusted certificate key id",
        I012_TRACE_CHAIN_BINDING: "Trace prefix must bind to the previous certificate and current action",
        I013_TRACE_STEP_ORDERING: "Chained execution steps must advance by exactly one step",
        I014_RECEIPT_CHAIN_BINDING: "Certificate must bind to the previous receipt hash",
    }

    return expectations.get(
        invariant,
        "The runtime invariant must hold before execution",
    )


__all__ = [
    "I001_CERTIFICATE_REQUIRED",
    "I002_CERTIFICATE_SIGNATURE",
    "I003_ACTION_HASH_BINDING",
    "I004_POLICY_HASH_BINDING",
    "I005_NONCE_BINDING",
    "I006_REPLAY_PROTECTION",
    "I007_POLICY_ADMISSION",
    "I008_TOOL_EXECUTION_BOUNDARY",
    "I009_POLICY_MANIFEST_INTEGRITY",
    "I010_CERTIFICATE_SIGNATURE_TAMPER",
    "I011_WRONG_CERTIFICATE_KEY",
    "I012_TRACE_CHAIN_BINDING",
    "I013_TRACE_STEP_ORDERING",
    "I014_RECEIPT_CHAIN_BINDING",
    "invariant_from_reason",
    "expected_for_invariant",
]
