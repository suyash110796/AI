from __future__ import annotations

import json
from pathlib import Path

from omega_runtime.core.counterexamples import format_counterexample
from omega_runtime.core.policy_manifest import DEFAULT_POLICY_PATH, write_default_policy_manifest
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.types import Action
from omega_runtime.core.verifier import issue_certificate


def main() -> None:
    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("policy tamper test", encoding="utf-8")

    # Start from a clean signed policy manifest.
    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    proxy = OmegaProxy()

    action = Action(
        run_id="run-policy-tamper",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="nonce-policy-tamper-001",
        declared_reason="Read allowed file under signed policy.",
    )

    ok, reason, cert = issue_certificate(action)
    print(f"VERIFIER: {'PASS' if ok else 'FAIL'} — {reason}")

    # Tamper with policy after certificate issuance.
    manifest = json.loads(DEFAULT_POLICY_PATH.read_text(encoding="utf-8"))
    manifest["policy"]["allowed_tools"] = []
    DEFAULT_POLICY_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    print("\nATTACK: policy manifest modified after certificate")
    result = proxy.execute(action, cert)

    print(f"POLICY TAMPER: {'ACCEPT' if result.accepted else 'REJECT'}")
    print(f"REASON: {result.reason}")

    if result.counterexample is not None:
        print()
        print(format_counterexample(result.counterexample))

    # Repair manifest after demo so future tests start clean.
    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    if result.accepted:
        raise SystemExit("ATTACK FAILED: tampered policy allowed action")

    print("\nFINAL: POLICY TAMPER BLOCKED")


if __name__ == "__main__":
    main()
