from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from omega_runtime.api import app
from omega_runtime.failure_lab import FAILURE_LAB_TYPE, run_failure_lab


def test_failure_lab_generates_accept_and_reject_scenarios(tmp_path):
    report = run_failure_lab(tmp_path / "failure_lab")

    assert report["lab_type"] == FAILURE_LAB_TYPE
    assert report["accepted"] is True
    assert report["reason"] == "failure lab passed"
    assert report["scenario_count"] == 5
    assert report["scenarios_passed"] == 5
    assert Path(report["report_path"]).exists()

    scenarios = {item["name"]: item for item in report["scenarios"]}

    assert scenarios["valid_system"]["actual_accept"] is True
    assert scenarios["valid_system"]["expected_accept"] is True
    assert scenarios["valid_system"]["passed"] is True

    assert scenarios["tampered_proof_bundle"]["actual_accept"] is False
    assert scenarios["tampered_proof_bundle"]["expected_accept"] is False
    assert scenarios["tampered_proof_bundle"]["passed"] is True

    assert scenarios["tampered_trace"]["actual_accept"] is False
    assert scenarios["tampered_trace"]["expected_accept"] is False
    assert scenarios["tampered_trace"]["passed"] is True

    assert scenarios["missing_proof_bundle"]["actual_accept"] is False
    assert scenarios["missing_trace"]["actual_accept"] is False


def test_failure_lab_status_route():
    client = TestClient(app)

    response = client.get("/failure-lab/status")

    assert response.status_code == 200
    payload = response.json()

    assert payload["accepted"] is True
    assert payload["failure_lab_type"] == FAILURE_LAB_TYPE
    assert payload["reason"] == "failure lab route healthy"


def test_failure_lab_dashboard_route():
    client = TestClient(app)

    response = client.get("/failure-lab")

    assert response.status_code == 200
    assert "Failure Demonstration Lab" in response.text
    assert "Tampered proof" in response.text
    assert "Run failure lab" in response.text


def test_failure_lab_run_route(tmp_path):
    client = TestClient(app)

    response = client.post(
        "/failure-lab/run",
        json={"output_dir": str(tmp_path / "failure_lab_api")},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["accepted"] is True
    assert payload["reason"] == "failure lab passed"
    assert payload["scenario_count"] == 5
    assert payload["scenarios_passed"] == 5
