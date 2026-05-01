from omega_runtime.core.canonical import sha256_hex
from omega_runtime.core.certificates import build_certificate, utc_now_iso
from omega_runtime.core.invariants import I007_POLICY_ADMISSION
from omega_runtime.core.policy import POLICY_HASH
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.types import Action, CertificatePayload


def test_counterexample_on_path_escape():
    proxy = OmegaProxy()

    action = Action(
        run_id="cx-path-test",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "../secret.txt"},
        nonce="cx-path-nonce",
    )

    # Deliberately build a cryptographically valid certificate for a policy-invalid action.
    # This proves the proxy still performs policy admission after certificate verification.
    payload = CertificatePayload(
        certificate_id="cert-cx-path-test-1",
        run_id=action.run_id,
        step_index=action.step_index,
        tool=action.tool,
        action_hash=sha256_hex(action),
        policy_hash=POLICY_HASH,
        nonce=action.nonce,
        issued_at=utc_now_iso(),
    )
    cert = build_certificate(payload)

    result = proxy.execute(action, cert)

    assert result.accepted is False
    assert result.counterexample is not None
    assert result.counterexample.failed_invariant == I007_POLICY_ADMISSION
    assert "path escapes sandbox" in result.counterexample.observed
    assert result.counterexample.decision == "REJECT"
