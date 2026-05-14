from __future__ import annotations

from fastapi.testclient import TestClient

from omega_runtime.api import app


client = TestClient(app)


def test_failure_lab_dashboard_page_exists():
    response = client.get("/failure-lab")

    assert response.status_code == 200
    assert "OMEGA Failure Lab Dashboard" in response.text
    assert "Show what the firewall catches" in response.text
    assert "/failure-lab/run" in response.text
    assert "/failure-lab/report" in response.text


def test_failure_lab_dashboard_alias_exists():
    response = client.get("/ui/failure-lab")

    assert response.status_code == 200
    assert "OMEGA verifier report" in response.text


def test_failure_lab_report_endpoint_shape_before_or_after_run():
    response = client.get("/failure-lab/report")

    assert response.status_code == 200
    payload = response.json()

    assert "accepted" in payload
    assert "reason" in payload
    assert payload["dashboard_version"] == "OMEGA_FAILURE_LAB_DASHBOARD_V1"
    assert "report_path" in payload
    assert "report_exists" in payload


def test_failure_lab_run_route_is_in_openapi():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]

    assert "/failure-lab/run" in paths
    assert "post" in paths["/failure-lab/run"]
    assert "/failure-lab/report" in paths
    assert "get" in paths["/failure-lab/report"]
