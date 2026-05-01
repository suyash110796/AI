from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Action:
    run_id: str
    step_index: int
    tool: str
    args: dict[str, Any]
    nonce: str
    declared_reason: str = ""


@dataclass(frozen=True)
class CertificatePayload:
    run_id: str
    step_index: int
    tool: str
    action_hash: str
    policy_hash: str
    nonce: str
    certificate_id: str = ""
    issued_at: str = ""
    decision: str = "ALLOW"



@dataclass(frozen=True)
class Certificate:
    payload: CertificatePayload
    payload_hash: str
    signature: str
    key_id: str
    signature_scheme: str = "ed25519"


@dataclass(frozen=True)
class Receipt:
    run_id: str
    step_index: int
    tool: str
    action_hash: str
    status: str
    output_hash: str
    detail: str = ""


@dataclass(frozen=True)
class Counterexample:
    counterexample_id: str
    run_id: str
    step_index: int
    failed_invariant: str
    expected: str
    observed: str
    decision: str = "REJECT"


@dataclass(frozen=True)
class ProxyResult:
    accepted: bool
    reason: str
    output: Any = None
    receipt: Receipt | None = None
    counterexample: Counterexample | None = None


@dataclass(frozen=True)
class ReplayResult:
    passed: bool
    reason: str
    entries_checked: int = 0
    final_entry_hash: str | None = None


@dataclass(frozen=True)
class VerifyResult:
    passed: bool
    reason: str
