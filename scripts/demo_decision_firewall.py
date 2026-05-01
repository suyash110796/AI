from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from omega_runtime.core.actions import Action
from omega_runtime.core.certificates import issue_certificate_for_action
from omega_runtime.core.decision_firewall import decision_firewall
from omega_runtime.core.ledger import reset_ledger
from omega_runtime.core.policy_manifest import DEFAULT_POLICY_PATH, write_default_policy_manifest
from omega_runtime.core.proof_bundle import export_proof_bundle
from omega_runtime.core.proxy import OmegaProxy


def main() -> None:
    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello decision firewall", encoding="utf-8")

    Path("traces").mkdir(exist_ok=True)
    Path("artifacts").mkdir(exist_ok=True)

    trace_path = Path("traces/decision-firewall-demo.jsonl")
    bundle_path = Path("artifacts/decision_firewall_bundle.json")

    reset_ledger(trace_path)

    action = Action(
        run_id="decision-firewall-demo",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="decision-firewall-demo-nonce",
    )

    certificate = issue_certificate_for_action(action)

    proxy = OmegaProxy(ledger_path=trace_path)
    result = proxy.execute(action, certificate)

    print(f"EXECUTION: {'ACCEPT' if result.accepted else 'REJECT'}")
    print(f"REASON: {result.reason}")

    if not result.accepted or result.receipt is None:
        print("FINAL: ACTION DID NOT RECEIVE TOOL RECEIPT")
        raise SystemExit(1)

    bundle = export_proof_bundle(
        path=bundle_path,
        action=action,
        certificate=certificate,
        receipt=result.receipt,
    )

    verdict = decision_firewall(
        proof_bundle_path=bundle_path,
        trace_path=trace_path,
    )

    print(f"TRACE: {trace_path}")
    print(f"PROOF BUNDLE: {bundle_path}")
    print(f"BUNDLE HASH: {bundle.get('bundle_hash')}")
    print(f"FIREWALL: {'ACCEPT' if verdict.accepted else 'REJECT'}")
    print(f"FIREWALL REASON: {verdict.reason}")
    print(f"FINAL ENTRY HASH: {verdict.final_entry_hash}")

    print("\nMACHINE VERDICT:")
    print(json.dumps(verdict.to_dict(), indent=2, sort_keys=True))

    raise SystemExit(0 if verdict.accepted else 1)


if __name__ == "__main__":
    main()
