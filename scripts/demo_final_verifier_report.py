from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from omega_runtime.core.actions import Action
from omega_runtime.core.episode_bundle import write_episode_bundle
from omega_runtime.core.final_verifier_report import (
    build_final_verifier_report,
    verify_final_verifier_report_json,
)
from omega_runtime.core.policy_manifest import DEFAULT_POLICY_PATH, write_default_policy_manifest
from omega_runtime.core.proof_bundle import write_proof_bundle
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.verifier import issue_certificate


def main() -> int:
    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    Path("sandbox").mkdir(exist_ok=True)
    Path("artifacts").mkdir(exist_ok=True)

    Path("sandbox/input.txt").write_text("hello final verifier", encoding="utf-8")

    run_id = "final-verifier-demo"
    proxy = OmegaProxy()

    action_1 = Action(
        run_id=run_id,
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce=f"{run_id}-nonce-1",
    )

    ok_1, reason_1, cert_1 = issue_certificate(action_1)
    if not ok_1:
        raise SystemExit(reason_1)

    result_1 = proxy.execute(action_1, cert_1)
    if not result_1.accepted:
        raise SystemExit(result_1.reason)

    final_output = f"Summary: {result_1.output}"

    action_2 = Action(
        run_id=run_id,
        step_index=2,
        tool="sandbox.write_file",
        args={
            "path": "sandbox/final_verifier_output.txt",
            "content": final_output,
        },
        nonce=f"{run_id}-nonce-2",
    )

    ok_2, reason_2, cert_2 = issue_certificate(action_2)
    if not ok_2:
        raise SystemExit(reason_2)

    result_2 = proxy.execute(action_2, cert_2)
    if not result_2.accepted:
        raise SystemExit(result_2.reason)

    proof_bundle_path = Path("artifacts/final_verifier_proof_bundle.json")
    episode_bundle_path = Path("artifacts/final_verifier_episode_bundle.json")
    final_report_path = Path("artifacts/final_verifier_report.json")

    write_proof_bundle(
        path=proof_bundle_path,
        action=action_1,
        certificate=cert_1,
        result=result_1,
    )

    write_episode_bundle(
        path=episode_bundle_path,
        run_id=run_id,
        final_output=final_output,
        steps=[
            {
                "action": action_1,
                "certificate": cert_1,
                "receipt": result_1.receipt,
            },
            {
                "action": action_2,
                "certificate": cert_2,
                "receipt": result_2.receipt,
            },
        ],
    )

    report = build_final_verifier_report(
        path=final_report_path,
        run_id=run_id,
        proof_bundle_path=proof_bundle_path,
        episode_bundle_path=episode_bundle_path,
    )

    verdict = verify_final_verifier_report_json(final_report_path)

    print("FINAL REPORT WRITTEN:", final_report_path)
    print("ACCEPTED:", verdict["accepted"])
    print("REASON:", verdict["reason"])
    print("REPORT HASH:", verdict["report_hash"])
    print()
    print("MACHINE VERDICT:")
    print(json.dumps(verdict, indent=2, sort_keys=True))

    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
