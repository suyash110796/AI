from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from omega_runtime.core.actions import Action
from omega_runtime.core.policy_manifest import DEFAULT_POLICY_PATH, write_default_policy_manifest
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.trace_chain import verify_trace_chain, write_trace_chain
from omega_runtime.core.verifier import issue_certificate


def main() -> int:
    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello trace chain", encoding="utf-8")

    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    proxy = OmegaProxy()

    executions = []

    for step_index, nonce in [
        (1, "trace-chain-demo-nonce-001"),
        (2, "trace-chain-demo-nonce-002"),
    ]:
        action = Action(
            run_id="trace-chain-demo",
            step_index=step_index,
            tool="sandbox.read_file",
            args={"path": "sandbox/input.txt"},
            nonce=nonce,
        )

        ok, reason, certificate = issue_certificate(action)
        if not ok or certificate is None:
            print(f"certificate_failed: {reason}")
            return 1

        result = proxy.execute(action, certificate)
        print(f"step_{step_index}_accepted: {result.accepted}")
        print(f"step_{step_index}_reason: {result.reason}")

        if not result.accepted or result.receipt is None:
            return 1

        executions.append((action, certificate, result.receipt))

    bundle_path = Path("artifacts/trace_chain_demo.json")
    bundle = write_trace_chain(path=bundle_path, executions=executions)

    verified, verify_reason = verify_trace_chain(bundle_path)

    print(f"trace_chain_path: {bundle_path}")
    print(f"trace_root_hash: {bundle['trace_root_hash']}")
    print(f"trace_hash: {bundle['trace_hash']}")
    print(f"trace_verified: {verified}")
    print(f"verify_reason: {verify_reason}")

    return 0 if verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
