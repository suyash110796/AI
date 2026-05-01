from dataclasses import replace
from pathlib import Path

from omega_runtime.core.invariants import I010_CERTIFICATE_SIGNATURE_TAMPER
from omega_runtime.core.policy_manifest import DEFAULT_POLICY_PATH, write_default_policy_manifest
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.types import Action
from omega_runtime.core.verifier import issue_certificate


def test_signature_tamper_rejected():
    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello", encoding="utf-8")

    proxy = OmegaProxy()

    action = Action(
        run_id="signature-tamper-test",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="signature-tamper-nonce",
    )

    ok, reason, cert = issue_certificate(action)
    assert ok, reason
    assert cert is not None

    tampered = replace(cert, signature="A" + cert.signature[1:])
    result = proxy.execute(action, tampered)

    assert result.accepted is False
    assert result.counterexample is not None
    assert result.counterexample.failed_invariant == I010_CERTIFICATE_SIGNATURE_TAMPER
