from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from omega_runtime.core.actions import Action
from omega_runtime.core.episode_bundle import write_episode_bundle
from omega_runtime.core.final_verifier_report import (
    REPORT_TYPE,
    build_final_verifier_report,
    verify_final_verifier_report,
    verify_final_verifier_report_json,
)
from omega_runtime.core.policy_manifest import DEFAULT_POLICY_PATH, write_default_policy_manifest
from omega_runtime.core.proof_bundle import write_proof_bundle
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.verifier import issue_certificate


def _make_artifacts(tmp_path):
    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    Path("sandbox").mkdir(exist_ok=True)
    Path("sandbox/input.txt").write_text("hello final report test", encoding="utf-8")

    run_id = "final-report-test"
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
        args={"path": "sandbox/final_report_output.txt", "content": final_output},
        nonce=f"{run_id}-nonce-2",
    )

    ok_2, reason_2, cert_2 = issue_certificate(action_2)
    assert ok_2, reason_2
    assert cert_2 is not None

    result_2 = proxy.execute(action_2, cert_2)
    assert result_2.accepted is True
    assert result_2.receipt is not None

    proof_bundle_path = tmp_path / "proof_bundle.json"
    episode_bundle_path = tmp_path / "episode_bundle.json"

    write_proof_bundle(
        path=proof_bundle_path,
        action=action_1,
        certificate=cert_1,
        result=result_1,
    )

    write_episode_bundle(
        path=episode_bundle_path,
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

    return run_id, proof_bundle_path, episode_bundle_path


def test_final_verifier_report_accepts_valid_artifacts(tmp_path):
    run_id, proof_bundle_path, episode_bundle_path = _make_artifacts(tmp_path)

    report_path = tmp_path / "final_report.json"

    report = build_final_verifier_report(
        path=report_path,
        run_id=run_id,
        proof_bundle_path=proof_bundle_path,
        episode_bundle_path=episode_bundle_path,
    )

    assert report_path.exists()
    assert report["report_type"] == REPORT_TYPE
    assert report["accepted"] is True
    assert report["component_count"] == 2
    assert report["report_hash"] is not None

    accepted, reason = verify_final_verifier_report(report_path)

    assert accepted is True
    assert reason == "final verifier report valid"


def test_final_verifier_report_detects_tamper(tmp_path):
    run_id, proof_bundle_path, episode_bundle_path = _make_artifacts(tmp_path)

    report_path = tmp_path / "final_report.json"

    build_final_verifier_report(
        path=report_path,
        run_id=run_id,
        proof_bundle_path=proof_bundle_path,
        episode_bundle_path=episode_bundle_path,
    )

    data = json.loads(report_path.read_text(encoding="utf-8"))
    data["run_id"] = "tampered-run-id"
    report_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    accepted, reason = verify_final_verifier_report(report_path)

    assert accepted is False
    assert reason == "final verifier report hash mismatch"


def test_final_verifier_report_json_payload(tmp_path):
    run_id, proof_bundle_path, episode_bundle_path = _make_artifacts(tmp_path)

    report_path = tmp_path / "final_report.json"

    build_final_verifier_report(
        path=report_path,
        run_id=run_id,
        proof_bundle_path=proof_bundle_path,
        episode_bundle_path=episode_bundle_path,
    )

    payload = verify_final_verifier_report_json(report_path)

    assert payload["accepted"] is True
    assert payload["reason"] == "final verifier report valid"
    assert payload["report_hash"] is not None
    assert payload["component_count"] == 2


def test_final_verifier_report_cli_accepts_valid_report(tmp_path):
    run_id, proof_bundle_path, episode_bundle_path = _make_artifacts(tmp_path)

    report_path = tmp_path / "final_report.json"

    build_final_verifier_report(
        path=report_path,
        run_id=run_id,
        proof_bundle_path=proof_bundle_path,
        episode_bundle_path=episode_bundle_path,
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/verify_final_report.py",
            str(report_path),
            "--json",
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr

    payload = json.loads(completed.stdout)

    assert payload["accepted"] is True
    assert payload["reason"] == "final verifier report valid"
    assert payload["report_hash"] is not None


def test_final_verifier_report_cli_rejects_tampered_report(tmp_path):
    run_id, proof_bundle_path, episode_bundle_path = _make_artifacts(tmp_path)

    report_path = tmp_path / "final_report.json"

    build_final_verifier_report(
        path=report_path,
        run_id=run_id,
        proof_bundle_path=proof_bundle_path,
        episode_bundle_path=episode_bundle_path,
    )

    data = json.loads(report_path.read_text(encoding="utf-8"))
    data["accepted"] = False
    report_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/verify_final_report.py",
            str(report_path),
            "--json",
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 1

    payload = json.loads(completed.stdout)

    assert payload["accepted"] is False
    assert payload["reason"] == "final verifier report hash mismatch"
