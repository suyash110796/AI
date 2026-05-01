from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from omega_runtime.core.counterexamples import format_counterexample
from omega_runtime.core.policy_manifest import DEFAULT_POLICY_PATH, write_default_policy_manifest
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.types import Action
from omega_runtime.core.verifier import issue_certificate


def main() -> None:
    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("signature tamper test", encoding="utf-8")

    proxy = OmegaProxy()

    action = Action(
        run_id="run-signature-tamper",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="nonce-signature-tamper-001",
        declared_reason="Read allowed file.",
    )

    ok, reason, cert = issue_certificate(action)
    print(f"VERIFIER: {'PASS' if ok else 'FAIL'} — {reason}")

    if cert is None:
        raise SystemExit("certificate was not issued")

    tampered_cert = replace(cert, signature="A" + cert.signature[1:])

    print("\nATTACK: certificate signature modified after issuance")
    result = proxy.execute(action, tampered_cert)

    print(f"SIGNATURE TAMPER: {'ACCEPT' if result.accepted else 'REJECT'}")
    print(f"REASON: {result.reason}")

    if result.counterexample is not None:
        print()
        print(format_counterexample(result.counterexample))

    if result.accepted:
        raise SystemExit("ATTACK FAILED: tampered signature allowed action")

    print("\nFINAL: SIGNATURE TAMPER BLOCKED")


if __name__ == "__main__":
    main()
