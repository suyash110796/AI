from fastapi.testclient import TestClient

from omega_runtime.api import app

client = TestClient(app)


def test_run_ledger_ui_page_exists():
    response = client.get("/run-ledger")

    assert response.status_code == 200
    assert "OMEGA Run Ledger Console" in response.text
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
    assert "latest_records" in payload
    assert "prompt_groups" in payload
    assert "comparison" in payload


def test_run_ledger_api_routes_are_in_openapi():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]

    assert "/run-ledger/api/summary" in paths
    assert "/run-ledger/api/record-dry-run" in paths
    assert "/run-ledger/api/record-live" in paths
    assert "/run-ledger/api/record-live-run" in paths


def test_run_ledger_ui_contains_live_openai_button():
    response = client.get("/ui/run-ledger")

    assert response.status_code == 200
    assert "Run LIVE OpenAI + record" in response.text
    assert "Run LIVE OpenAI + Record" in response.text
    assert "/run-ledger/api/record-live-run" in response.text


def test_run_ledger_dry_run_route_records_without_api_key():
    response = client.post(
        "/run-ledger/api/record-dry-run",
        data={
            "prompt": "Dry-run route smoke test.",
            "model": "gpt-4.1-mini",
            "max_output_tokens": "16",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["accepted"] is True
    assert payload["live"] is False
    assert payload["mode"] == "dry_run"
    assert payload["ledger_recorded"] is True
    assert payload["message"] == "Dry-run OpenAI run recorded"


def test_run_ledger_live_route_is_registered_without_calling_paid_api():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]

    assert "/run-ledger/api/record-live" in paths
    assert "/run-ledger/api/record-live-run" in paths
