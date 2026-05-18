from __future__ import annotations

from fastapi.testclient import TestClient

from omega_runtime.api import app


client = TestClient(app)


def test_run_ledger_ui_page_exists():
    response = client.get("/run-ledger")

    assert response.status_code == 200
    assert "OMEGA Run Ledger Console" in response.text
    assert "/run-ledger/api/summary" in response.text
    assert "/run-ledger/api/record-dry-run" in response.text


def test_run_ledger_ui_alias_exists():
    response = client.get("/ui/run-ledger")

    assert response.status_code == 200
    assert "OMEGA_RUN_LEDGER_UI_V1" in response.text


def test_run_ledger_summary_endpoint_shape():
    response = client.get("/run-ledger/api/summary")

    assert response.status_code == 200
    payload = response.json()

    assert payload["accepted"] is True
    assert payload["ledger_ui_version"] == "OMEGA_RUN_LEDGER_UI_V1"
    assert "ledger_path" in payload
    assert "ledger_exists" in payload
    assert "records_found" in payload
    assert "records" in payload
    assert "prompt_groups" in payload
    assert "latest_comparison" in payload


def test_run_ledger_api_routes_are_in_openapi():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]

    assert "/run-ledger/api/summary" in paths
    assert "get" in paths["/run-ledger/api/summary"]

    assert "/run-ledger/api/record-dry-run" in paths
    assert "post" in paths["/run-ledger/api/record-dry-run"]
