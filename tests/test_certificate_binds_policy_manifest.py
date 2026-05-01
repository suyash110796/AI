from dataclasses import replace
from pathlib import Path

from omega_runtime.core.invariants import I004_POLICY_HASH_BINDING
from omega_runtime.core.policy_manifest import DEFAULT_POLICY_PATH, write_default_policy_manifest
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.types import Action
from omega_runtime.core.verifier import issue_certificate


def test_certificate_binds_policy_manifest():
    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello", encoding="utf-8")

    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    proxy = OmegaProxy()

    action = Action(
        run_id="policy-bind-test",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="policy-bind-nonce",
    )

    ok, reason, cert = issue_certificate(action)
    assert ok, reason

    forged_payload = replace(cert.payload, policy_hash="f" * 64)
    forged_cert = replace(cert, payload=forged_payload)

    result = proxy.execute(action, forged_cert)

    assert result.accepted is False
    assert result.counterexample is not None
    assert result.counterexample.failed_invariant in {
        I004_POLICY_HASH_BINDING,
        "I002_CERTIFICATE_SIGNATURE",
    }
