import json
from pathlib import Path

from omega_runtime.core.invariants import I009_POLICY_MANIFEST_INTEGRITY
from omega_runtime.core.policy_manifest import DEFAULT_POLICY_PATH, write_default_policy_manifest
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.types import Action
from omega_runtime.core.verifier import issue_certificate


def test_policy_manifest_tamper_rejected():
    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello", encoding="utf-8")

    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    proxy = OmegaProxy()

    action = Action(
        run_id="policy-tamper-test",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="policy-tamper-nonce",
    )

    ok, reason, cert = issue_certificate(action)
    assert ok, reason

    manifest = json.loads(DEFAULT_POLICY_PATH.read_text(encoding="utf-8"))
    manifest["policy"]["allowed_tools"] = []
    DEFAULT_POLICY_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    result = proxy.execute(action, cert)

    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    assert result.accepted is False
    assert result.counterexample is not None
    assert result.counterexample.failed_invariant == I009_POLICY_MANIFEST_INTEGRITY
    assert "policy manifest" in result.counterexample.observed
