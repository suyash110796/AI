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
    Path("sandbox/input.txt").write_text("wrong key test", encoding="utf-8")

    proxy = OmegaProxy()

    action = Action(
        run_id="run-wrong-key",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="nonce-wrong-key-001",
        declared_reason="Read allowed file.",
    )

    ok, reason, cert = issue_certificate(action)
    print(f"VERIFIER: {'PASS' if ok else 'FAIL'} — {reason}")

    if cert is None:
        raise SystemExit("certificate was not issued")

    wrong_key_cert = replace(cert, key_id="attacker-key-id")

    print("\nATTACK: certificate claims wrong key id")
    result = proxy.execute(action, wrong_key_cert)

    print(f"WRONG KEY: {'ACCEPT' if result.accepted else 'REJECT'}")
    print(f"REASON: {result.reason}")

    if result.counterexample is not None:
        print()
        print(format_counterexample(result.counterexample))

    if result.accepted:
        raise SystemExit("ATTACK FAILED: wrong key allowed action")

    print("\nFINAL: WRONG KEY BLOCKED")


if __name__ == "__main__":
    main()
