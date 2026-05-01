from dataclasses import replace
from pathlib import Path

from omega_runtime.core.invariants import I011_WRONG_CERTIFICATE_KEY
from omega_runtime.core.policy_manifest import DEFAULT_POLICY_PATH, write_default_policy_manifest
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.types import Action
from omega_runtime.core.verifier import issue_certificate


def test_wrong_key_rejected():
    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello", encoding="utf-8")

    proxy = OmegaProxy()

    action = Action(
        run_id="wrong-key-test",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="wrong-key-nonce",
    )

    ok, reason, cert = issue_certificate(action)
    assert ok, reason
    assert cert is not None

    wrong_key_cert = replace(cert, key_id="attacker-key-id")
    result = proxy.execute(action, wrong_key_cert)

    assert result.accepted is False
    assert result.counterexample is not None
    assert result.counterexample.failed_invariant == I011_WRONG_CERTIFICATE_KEY
