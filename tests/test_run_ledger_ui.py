from fastapi.testclient import TestClient

from omega_runtime.api import app

client = TestClient(app)


def test_run_ledger_ui_page_exists():
    response = client.get("/run-ledger")

    assert response.status_code == 200
    assert "OMEGA Run Ledger Console" in response.text
    assert "Evidence Inspector" in response.text
    assert "/run-ledger/api/summary" in response.text


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
    assert "comparison" in payload
    assert "insights" in payload
    assert "live_records" in payload
    assert "dry_run_records" in payload
    assert "response_variants" in payload


def test_run_ledger_api_routes_are_in_openapi():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]

    assert "/run-ledger/api/summary" in paths
    assert "/run-ledger/api/record-dry-run" in paths
    assert "/run-ledger/api/record-live" in paths
    assert "/run-ledger/api/record-live-run" in paths


def test_run_ledger_ui_contains_live_openai_button_without_calling_paid_api():
    response = client.get("/ui/run-ledger")

    assert response.status_code == 200
    assert "Run LIVE OpenAI + Record" in response.text
    assert "Run LIVE OpenAI + record" in response.text
    assert "/run-ledger/api/record-live-run" in response.text
    assert "OPENAI_API_KEY" in response.text
    assert "This can spend API credits" in response.text


def test_run_ledger_ui_contains_transparency_sections():
    response = client.get("/ui/run-ledger")

    assert response.status_code == 200
    assert "same prompt, response drift" in response.text
    assert "Latest two-run comparison" in response.text
    assert "Machine-readable insight receipt" in response.text
    assert "Latest recorded runs" in response.text
