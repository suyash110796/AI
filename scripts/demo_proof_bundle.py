from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from omega_runtime.core.actions import Action
from omega_runtime.core.proof_bundle import verify_proof_bundle, write_proof_bundle
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.verifier import issue_certificate
from omega_runtime.core.policy_manifest import DEFAULT_POLICY_PATH, write_default_policy_manifest


def main() -> None:
    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello proof bundle demo", encoding="utf-8")

    action = Action(
        run_id="proof-bundle-demo",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="proof-bundle-demo-nonce",
    )

    ok, reason, certificate = issue_certificate(action)
    if not ok or certificate is None:
        raise SystemExit(f"certificate rejected: {reason}")

    result = OmegaProxy().execute(action, certificate)

    bundle_path = Path("artifacts/proof_bundle_demo.json")
    bundle = write_proof_bundle(
        action=action,
        certificate=certificate,
        result=result,
        path=bundle_path,
    )

    verified, verify_reason = verify_proof_bundle(bundle_path)

    print("accepted:", result.accepted)
    print("reason:", result.reason)
    print("bundle_path:", bundle_path)
    print("bundle_hash:", bundle["bundle_hash"])
    print("bundle_verified:", verified)
    print("verify_reason:", verify_reason)


if __name__ == "__main__":
    main()
