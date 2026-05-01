from __future__ import annotations

from pathlib import Path

from omega_runtime.core.ledger import reset_ledger
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.replay import replay_trace
from omega_runtime.core.types import Action
from omega_runtime.core.verifier import issue_certificate


def main() -> None:
    trace_path = Path("traces/run-001.jsonl")
    reset_ledger(trace_path)

    proxy = OmegaProxy(ledger_path=trace_path)
    run_id = "run-001"

    print(f"RUN: {run_id}")

    read_action = Action(
        run_id=run_id,
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="nonce-read-001",
        declared_reason="Read input file.",
    )

    ok, reason, read_cert = issue_certificate(read_action)
    print("\nSTEP 1: READ_FILE sandbox/input.txt")
    print(f"VERIFIER: {'PASS' if ok else 'FAIL'} — {reason}")

    read_result = proxy.execute(read_action, read_cert)
    print(f"PROXY: {'ACCEPT' if read_result.accepted else 'REJECT'} — {read_result.reason}")
    print(f"TOOL EXECUTED: {read_result.accepted}")

    if not read_result.accepted:
        raise SystemExit("read failed")

    summary = f"SUMMARY: {read_result.output.strip()}"

    write_action = Action(
        run_id=run_id,
        step_index=2,
        tool="sandbox.write_file",
        args={"path": "sandbox/output.txt", "content": summary},
        nonce="nonce-write-001",
        declared_reason="Write summary output.",
    )

    ok, reason, write_cert = issue_certificate(write_action)
    print("\nSTEP 2: WRITE_FILE sandbox/output.txt")
    print(f"VERIFIER: {'PASS' if ok else 'FAIL'} — {reason}")

    write_result = proxy.execute(write_action, write_cert)
    print(f"PROXY: {'ACCEPT' if write_result.accepted else 'REJECT'} — {write_result.reason}")
    print(f"TOOL EXECUTED: {write_result.accepted}")

    if not write_result.accepted:
        raise SystemExit("write failed")

    replay_result = replay_trace(trace_path)
    print(f"\nOFFLINE REPLAY: {'PASS' if replay_result.passed else 'FAIL'} — {replay_result.reason}")
    print(f"TRACE: {trace_path}")
    print("FINAL: LAWFUL TRACE")


if __name__ == "__main__":
    main()
