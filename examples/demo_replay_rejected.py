from __future__ import annotations

from pathlib import Path

from omega_runtime.core.ledger import reset_ledger
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.types import Action
from omega_runtime.core.verifier import issue_certificate


def main() -> None:
    trace_path = Path("traces/run-replay.jsonl")
    reset_ledger(trace_path)
    proxy = OmegaProxy(ledger_path=trace_path)

    action = Action(
        run_id="run-replay",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="nonce-replay-001",
        declared_reason="Read allowed file once.",
    )

    ok, reason, cert = issue_certificate(action)
    print(f"VERIFIER: {'PASS' if ok else 'FAIL'} — {reason}")

    first = proxy.execute(action, cert)
    print(f"FIRST EXECUTION: {'ACCEPT' if first.accepted else 'REJECT'} — {first.reason}")

    second = proxy.execute(action, cert)
    print(f"REPLAY EXECUTION: {'ACCEPT' if second.accepted else 'REJECT'} — {second.reason}")

    if second.accepted:
        raise SystemExit("ATTACK FAILED: replay executed")

    print(f"TRACE: {trace_path}")
    print("FINAL: REPLAY BLOCKED")


if __name__ == "__main__":
    main()
