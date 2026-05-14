from __future__ import annotations

from fastapi.testclient import TestClient

from omega_runtime.api import app


client = TestClient(app)


def test_dashboard_root_renders():
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "OMEGA Runtime Dashboard" in response.text
    assert "Proof-carrying execution" in response.text


def test_dashboard_ui_alias_renders():
    response = client.get("/ui")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Execution lifecycle" in response.text
    assert "Machine output" in response.text


def test_dashboard_does_not_break_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["reason"] == "healthy"
