from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from omega_runtime.core.episode_bundle import (
    export_episode_bundle,
    verify_episode_bundle,
    verify_episode_bundle_json,
    write_episode_bundle,
)
from omega_runtime.core.policy_manifest import DEFAULT_POLICY_PATH, write_default_policy_manifest
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.types import Action
from omega_runtime.core.verifier import issue_certificate


def _make_two_step_episode(tmp_path):
    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello episode test", encoding="utf-8")

    run_id = "episode-test"
    proxy = OmegaProxy()

    action_1 = Action(
        run_id=run_id,
        step_index=1,
        tool="sandbox.read_file",
        args={"path": "sandbox/input.txt"},
        nonce=f"{run_id}-nonce-1",
    )

    ok_1, reason_1, cert_1 = issue_certificate(action_1)
    assert ok_1, reason_1
    assert cert_1 is not None

    result_1 = proxy.execute(action_1, cert_1)
    assert result_1.accepted is True
    assert result_1.receipt is not None

    final_output = f"Summary: {result_1.output}"

    action_2 = Action(
        run_id=run_id,
        step_index=2,
        tool="sandbox.write_file",
        args={"path": "sandbox/episode_test_output.txt", "content": final_output},
        nonce=f"{run_id}-nonce-2",
    )

    ok_2, reason_2, cert_2 = issue_certificate(action_2)
    assert ok_2, reason_2
    assert cert_2 is not None

    result_2 = proxy.execute(action_2, cert_2)
    assert result_2.accepted is True
    assert result_2.receipt is not None

    bundle_path = tmp_path / "episode_bundle.json"
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

    return bundle_path, bundle


def test_episode_bundle_valid(tmp_path):
    bundle_path, bundle = _make_two_step_episode(tmp_path)

    assert bundle["bundle_type"] == "OMEGA_EPISODE_BUNDLE_V1"
    assert bundle["step_count"] == 2
    assert bundle["verification_summary"]["all_certificates_bound"] is True
    assert bundle["verification_summary"]["all_receipts_bound"] is True
    assert bundle["verification_summary"]["all_receipts_executed"] is True

    accepted, reason = verify_episode_bundle(bundle_path)

    assert accepted is True
    assert reason == "episode bundle valid"


def test_episode_bundle_rejects_final_output_tamper(tmp_path):
    bundle_path, _bundle = _make_two_step_episode(tmp_path)

    data = json.loads(bundle_path.read_text(encoding="utf-8"))
    data["final_output"] = "malicious altered final answer"
    bundle_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    accepted, reason = verify_episode_bundle(bundle_path)

    assert accepted is False
    assert reason == "episode bundle hash mismatch"


def test_episode_bundle_rejects_action_tamper_after_rehash(tmp_path):
    bundle_path, _bundle = _make_two_step_episode(tmp_path)

    data = json.loads(bundle_path.read_text(encoding="utf-8"))
    data["steps"][0]["action"]["args"]["path"] = "sandbox/evil.txt"

    # Attacker cannot forge the original bundle hash, so this catches first.
    bundle_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    accepted, reason = verify_episode_bundle(bundle_path)

    assert accepted is False
    assert reason == "episode bundle hash mismatch"


def test_episode_bundle_json_verdict(tmp_path):
    bundle_path, bundle = _make_two_step_episode(tmp_path)

    payload = verify_episode_bundle_json(bundle_path)

    assert payload["accepted"] is True
    assert payload["reason"] == "episode bundle valid"
    assert payload["bundle_hash"] == bundle["bundle_hash"]


def test_episode_bundle_cli_accepts_valid_bundle(tmp_path):
    bundle_path, _bundle = _make_two_step_episode(tmp_path)

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/verify_episode_bundle.py",
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
    assert payload["reason"] == "episode bundle valid"
    assert payload["bundle_hash"] is not None


def test_episode_bundle_cli_rejects_tampered_bundle(tmp_path):
    bundle_path, _bundle = _make_two_step_episode(tmp_path)

    data = json.loads(bundle_path.read_text(encoding="utf-8"))
    data["final_output"] = "tampered"
    bundle_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/verify_episode_bundle.py",
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
    assert payload["reason"] == "episode bundle hash mismatch"
