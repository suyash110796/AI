from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from omega_runtime.core.actions import Action
from omega_runtime.core.proof_bundle import export_proof_bundle
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.verifier import issue_certificate


def test_proof_bundle_cli_accepts_valid_bundle(tmp_path):
    sandbox = Path("sandbox")
    sandbox.mkdir(exist_ok=True)
    (sandbox / "input.txt").write_text("hello offline verifier", encoding="utf-8")

    action = Action(
        run_id="cli-proof-valid",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="cli-proof-valid-nonce",
    )

    ok, reason, cert = issue_certificate(action)
    assert ok, reason
    assert cert is not None

    proxy = OmegaProxy()
    result = proxy.execute(action, cert)
    assert result.accepted is True
    assert result.receipt is not None

    bundle_path = tmp_path / "valid_bundle.json"
    export_proof_bundle(
        path=bundle_path,
        action=action,
        certificate=cert,
        receipt=result.receipt,
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/verify_proof_bundle.py",
            str(bundle_path),
            "--json",
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr

    payload = json.loads(completed.stdout)
    assert payload["accepted"] is True
    assert payload["reason"] == "proof bundle valid"
    assert payload["bundle_hash"] is not None


def test_proof_bundle_cli_rejects_tampered_bundle(tmp_path):
    sandbox = Path("sandbox")
    sandbox.mkdir(exist_ok=True)
    (sandbox / "input.txt").write_text("hello tamper verifier", encoding="utf-8")

    action = Action(
        run_id="cli-proof-tamper",
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce="cli-proof-tamper-nonce",
    )

    ok, reason, cert = issue_certificate(action)
    assert ok, reason
    assert cert is not None

    proxy = OmegaProxy()
    result = proxy.execute(action, cert)
    assert result.accepted is True
    assert result.receipt is not None

    bundle_path = tmp_path / "tampered_bundle.json"
    export_proof_bundle(
        path=bundle_path,
        action=action,
        certificate=cert,
        receipt=result.receipt,
    )

    data = json.loads(bundle_path.read_text(encoding="utf-8"))

    # Mutate the bundled action after export. Offline verification must reject it.
    if "action" in data and "args" in data["action"]:
        data["action"]["args"]["path"] = "sandbox/evil.txt"
    elif "action" in data and "payload" in data["action"]:
        data["action"]["payload"]["args"]["path"] = "sandbox/evil.txt"
    else:
        data["tamper_marker"] = "tampered"

    bundle_path.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/verify_proof_bundle.py",
            str(bundle_path),
            "--json",
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 1

    payload = json.loads(completed.stdout)
    assert payload["accepted"] is False
    assert payload["reason"] != "proof bundle valid"
