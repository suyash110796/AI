from __future__ import annotations

from pathlib import Path

from omega_runtime.core.canonical import sha256_hex
from omega_runtime.core.certificates import (
    TRUSTED_CERTIFICATE_KEY_ID,
    verify_certificate,
)
from omega_runtime.core.counterexamples import build_counterexample
from omega_runtime.core.ledger import record_decision
from omega_runtime.core.policy import POLICY_HASH, evaluate_action
from omega_runtime.core.policy_manifest import DEFAULT_POLICY_PATH, verify_policy_manifest
from omega_runtime.core.types import Action, Certificate, ProxyResult, Receipt
from omega_runtime.tools import sandbox_tools


class OmegaProxy:
    def __init__(self, ledger_path: str | Path | None = None) -> None:
        self.used_nonces: set[str] = set()
        self.ledger_path = ledger_path

    def _record(
        self,
        *,
        action: Action,
        action_hash: str,
        certificate_hash: str | None,
        receipt_hash: str | None,
        verdict: str,
        reason: str,
    ) -> None:
        if self.ledger_path is None:
            return

        record_decision(
            ledger_path=self.ledger_path,
            run_id=action.run_id,
            step_index=action.step_index,
            action_hash=action_hash,
            certificate_hash=certificate_hash,
            receipt_hash=receipt_hash,
            verdict=verdict,
            reason=reason,
        )

    def _reject(
        self,
        *,
        action: Action,
        action_hash: str,
        certificate_hash: str | None,
        reason: str,
    ) -> ProxyResult:
        counterexample = build_counterexample(
            action=action,
            reason=reason,
        )

        self._record(
            action=action,
            action_hash=action_hash,
            certificate_hash=certificate_hash,
            receipt_hash=None,
            verdict="REJECT",
            reason=reason,
        )

        return ProxyResult(
            accepted=False,
            reason=reason,
            counterexample=counterexample,
        )

    def execute(self, action: Action, certificate: Certificate | None) -> ProxyResult:
        action_hash = sha256_hex(action)
        certificate_hash = sha256_hex(certificate) if certificate is not None else None

        manifest_ok, manifest_reason, active_manifest_hash = verify_policy_manifest(
            DEFAULT_POLICY_PATH
        )
        if not manifest_ok:
            return self._reject(
                action=action,
                action_hash=action_hash,
                certificate_hash=certificate_hash,
                reason=manifest_reason,
            )

        # Gate 1: certificate must exist.
        if certificate is None:
            return self._reject(
                action=action,
                action_hash=action_hash,
                certificate_hash=None,
                reason="no certificate",
            )

        # Gate 2: wrong-key classification must happen BEFORE signature verification.
        # Otherwise a wrong key gets misclassified as generic signature tamper.
        if getattr(certificate, "key_id", None) != TRUSTED_CERTIFICATE_KEY_ID:
            return self._reject(
                action=action,
                action_hash=action_hash,
                certificate_hash=certificate_hash,
                reason="wrong certificate key",
            )

        # Gate 3: policy hash binding must happen BEFORE signature verification.
        # The test deliberately forges payload.policy_hash; if signature verification
        # runs first, it is misclassified as I010 instead of I004.
        if certificate.payload.policy_hash != POLICY_HASH:
            return self._reject(
                action=action,
                action_hash=action_hash,
                certificate_hash=certificate_hash,
                reason="policy_hash mismatch",
            )

        if (
            active_manifest_hash is not None
            and certificate.payload.policy_hash != active_manifest_hash
        ):
            return self._reject(
                action=action,
                action_hash=action_hash,
                certificate_hash=certificate_hash,
                reason="policy_hash mismatch",
            )

        # Gate 4: cryptographic certificate signature verification.
        if certificate.key_id != TRUSTED_CERTIFICATE_KEY_ID:
            return self._reject(
                action=action,
                action_hash=action_hash,
                certificate_hash=certificate_hash,
                reason="wrong certificate key",
            )

        cert_ok, cert_reason = verify_certificate(certificate)
        if not cert_ok:
            return self._reject(
                action=action,
                action_hash=action_hash,
                certificate_hash=certificate_hash,
                reason=cert_reason,
            )

        # Gate 5: action hash binding.
        if certificate.payload.action_hash != action_hash:
            return self._reject(
                action=action,
                action_hash=action_hash,
                certificate_hash=certificate_hash,
                reason="action_hash mismatch",
            )

        # Gate 6: nonce binding.
        if certificate.payload.nonce != action.nonce:
            return self._reject(
                action=action,
                action_hash=action_hash,
                certificate_hash=certificate_hash,
                reason="nonce mismatch",
            )

        # Gate 7: replay rejection.
        if action.nonce in self.used_nonces:
            return self._reject(
                action=action,
                action_hash=action_hash,
                certificate_hash=certificate_hash,
                reason="replay rejected: nonce already used",
            )

        # Gate 8: policy admission.
        allowed, reason = evaluate_action(action)
        if not allowed:
            return self._reject(
                action=action,
                action_hash=action_hash,
                certificate_hash=certificate_hash,
                reason=reason,
            )

        try:
            if action.tool == "sandbox.read_file":
                output = sandbox_tools.read_file(action.args["path"])

            elif action.tool == "sandbox.write_file":
                output = sandbox_tools.write_file(
                    path=action.args["path"],
                    content=action.args["content"],
                )

            else:
                return self._reject(
                    action=action,
                    action_hash=action_hash,
                    certificate_hash=certificate_hash,
                    reason=f"unknown tool: {action.tool}",
                )

        except Exception as exc:
            return self._reject(
                action=action,
                action_hash=action_hash,
                certificate_hash=certificate_hash,
                reason=f"tool error: {exc}",
            )

        self.used_nonces.add(action.nonce)

        receipt = Receipt(
            run_id=action.run_id,
            step_index=action.step_index,
            tool=action.tool,
            action_hash=action_hash,
            status="EXECUTED",
            output_hash=sha256_hex(output),
            detail="tool executed through OmegaProxy",
        )

        receipt_hash = sha256_hex(receipt)

        self._record(
            action=action,
            action_hash=action_hash,
            certificate_hash=certificate_hash,
            receipt_hash=receipt_hash,
            verdict="ACCEPT",
            reason="proxy accept",
        )

        return ProxyResult(
            accepted=True,
            reason="proxy accept",
            output=output,
            receipt=receipt,
            counterexample=None,
        )