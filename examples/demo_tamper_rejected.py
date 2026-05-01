from __future__ import annotations

from omega_runtime.core.counterexamples import format_counterexample
from omega_runtime.core.ledger import reset_ledger
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.types import Action
from omega_runtime.core.verifier import issue_certificate


def main() -> None:
    run_id = "run-tamper"
    trace_path = reset_ledger(run_id)
    proxy = OmegaProxy(ledger_path=trace_path)

    original_action = Action(
        run_id=run_id,
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="nonce-attack-001",
        declared_reason="Read allowed file.",
    )

    ok, reason, cert = issue_certificate(original_action)
    print(f"VERIFIER: {'PASS' if ok else 'FAIL'} — {reason}")

    tampered_action = Action(
        run_id=run_id,
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/evil.txt"},
        nonce="nonce-attack-001",
        declared_reason="Read allowed file.",
    )

    print("\nATTACK: action modified after certificate")
    result = proxy.execute(tampered_action, cert)

    print(f"PROXY: {'ACCEPT' if result.accepted else 'REJECT'}")
    print(f"REASON: {result.reason}")
    print(f"TOOL EXECUTED: {result.accepted}")

    if result.counterexample is not None:
        print()
        print(format_counterexample(result.counterexample))

    print(f"\nTRACE: {trace_path}")

    if result.accepted:
        raise SystemExit("ATTACK FAILED: tampered action executed")

    print("FINAL: TAMPER BLOCKED")


if __name__ == "__main__":
    main()
