from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from omega_runtime.core.episode_bundle import verify_episode_bundle, write_episode_bundle
from omega_runtime.core.policy_manifest import DEFAULT_POLICY_PATH, write_default_policy_manifest
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.types import Action
from omega_runtime.core.verifier import issue_certificate


def main() -> None:
    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello episode runtime", encoding="utf-8")

    run_id = "episode-demo-001"
    proxy = OmegaProxy()

    action_1 = Action(
        run_id=run_id,
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="episode-demo-nonce-001",
    )

    ok_1, reason_1, cert_1 = issue_certificate(action_1)
    if not ok_1 or cert_1 is None:
        raise RuntimeError(reason_1)

    result_1 = proxy.execute(action_1, cert_1)
    if not result_1.accepted or result_1.receipt is None:
        raise RuntimeError(result_1.reason)

    final_output = f"Summary: {result_1.output}"

    action_2 = Action(
        run_id=run_id,
        step_index=2,
        tool="sandbox.write_file",
        args={"path": "sandbox/episode_output.txt", "content": final_output},
        nonce="episode-demo-nonce-002",
    )

    ok_2, reason_2, cert_2 = issue_certificate(action_2)
    if not ok_2 or cert_2 is None:
        raise RuntimeError(reason_2)

    result_2 = proxy.execute(action_2, cert_2)
    if not result_2.accepted or result_2.receipt is None:
        raise RuntimeError(result_2.reason)

    bundle_path = Path("artifacts/episode_bundle_demo.json")
    bundle = write_episode_bundle(
        path=bundle_path,
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

    accepted, verify_reason = verify_episode_bundle(bundle_path)

    print("EPISODE BUNDLE:", bundle_path)
    print("RUN:", run_id)
    print("STEPS:", bundle["step_count"])
    print("FINAL ANSWER HASH:", bundle["final_answer_hash"])
    print("EPISODE TRACE HASH:", bundle["episode_trace_hash"])
    print("BUNDLE HASH:", bundle["bundle_hash"])
    print("VERIFIED:", accepted)
    print("VERIFY REASON:", verify_reason)
    print()
    print("MACHINE VERDICT:")
    print(
        json.dumps(
            {
                "accepted": accepted,
                "reason": verify_reason,
                "bundle_hash": bundle["bundle_hash"],
                "episode_trace_hash": bundle["episode_trace_hash"],
                "step_count": bundle["step_count"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
