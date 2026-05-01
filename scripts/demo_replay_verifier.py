from __future__ import annotations

from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from omega_runtime.core.actions import Action
from omega_runtime.core.ledger import reset_ledger
from omega_runtime.core.policy_manifest import DEFAULT_POLICY_PATH, write_default_policy_manifest
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.replay_verifier import result_to_dict, verify_replay_trace
from omega_runtime.core.verifier import issue_certificate


def main() -> int:
    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    sandbox = Path("sandbox")
    sandbox.mkdir(exist_ok=True)
    (sandbox / "input.txt").write_text("hello replay verifier", encoding="utf-8")

    trace_path = Path("traces") / "replay-verifier-demo.jsonl"
    trace_path.parent.mkdir(exist_ok=True)
    reset_ledger(trace_path)

    action = Action(
        run_id="replay-verifier-demo",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="replay-verifier-demo-nonce",
    )

    ok, reason, certificate = issue_certificate(action)
    if not ok or certificate is None:
        print("CERTIFICATE: FAIL")
        print(f"REASON: {reason}")
        return 1

    proxy = OmegaProxy(ledger_path=trace_path)
    execution = proxy.execute(action, certificate)

    print(f"EXECUTION: {'ACCEPT' if execution.accepted else 'REJECT'}")
    print(f"REASON: {execution.reason}")
    print(f"TRACE: {trace_path}")

    replay = verify_replay_trace(trace_path)

    print(f"REPLAY VERIFIER: {'PASS' if replay.passed else 'FAIL'}")
    print(f"REPLAY REASON: {replay.reason}")
    print(f"ENTRIES CHECKED: {replay.entries_checked}")
    print(f"FINAL ENTRY HASH: {replay.final_entry_hash}")

    print("\nMACHINE VERDICT:")
    print(json.dumps(result_to_dict(replay), indent=2, sort_keys=True))

    return 0 if replay.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
