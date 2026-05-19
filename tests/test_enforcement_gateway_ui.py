
from fastapi.testclient import TestClient

from omega_runtime.api import app


client = TestClient(app)


def test_enforcement_gateway_ui_page_exists():
    response = client.get("/ui/enforcement-gateway")

    assert response.status_code == 200
    assert "OMEGA Enforcement Gateway Console" in response.text
    assert "This is the firewall view" in response.text
    assert "OpenAI called" in response.text
    assert "/enforcement-gateway/api/summary" in response.text


def test_enforcement_gateway_ui_root_alias_exists():
    response = client.get("/enforcement-gateway")

    assert response.status_code == 200
    assert "OMEGA_ENFORCEMENT_GATEWAY_UI_V1" in response.text
    assert "Back to Run Ledger" in response.text


def test_enforcement_gateway_summary_shape():
    response = client.get("/enforcement-gateway/api/summary")

    assert response.status_code == 200
    payload = response.json()

    assert payload["accepted"] is True
    assert payload["gateway_ui_version"] == "OMEGA_ENFORCEMENT_GATEWAY_UI_V1"
    assert "ledger_path" in payload
    assert "ledger_exists" in payload
    assert "records_scanned" in payload
    assert "gateway_events_found" in payload
    assert "allowed_events" in payload
    assert "blocked_events" in payload
    assert "openai_called_events" in payload
    assert "openai_not_called_events" in payload
    assert "top_violations" in payload
    assert "events" in payload
    assert isinstance(payload["events"], list)


def test_enforcement_gateway_routes_are_in_openapi():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]

    assert "/enforcement-gateway" in paths
    assert "/ui/enforcement-gateway" in paths
    assert "/enforcement-gateway/api/summary" in paths

def test_enforcement_gateway_ui_metric_clarity_copy():
    response = client.get("/enforcement-gateway")

    assert response.status_code == 200
    assert "OMEGA_UI_METRIC_CLARITY_V1" in response.text
    assert "enforcement-decision counters, not model-quality scores" in response.text
    assert "Gateway decision coverage" in response.text or "Allowed" in response.text
    assert "Top violation signals" in response.text
