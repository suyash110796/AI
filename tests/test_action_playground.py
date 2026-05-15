
from fastapi.testclient import TestClient
from omega_runtime.api import app

client = TestClient(app)

def test_action_playground_page_exists():
    r = client.get("/action-playground")
    assert r.status_code == 200
    assert "OMEGA Agent Action Playground" in r.text
    assert "Run selected action" in r.text

def test_action_playground_scenarios():
    r = client.get("/action-playground/scenarios")
    assert r.status_code == 200
    p = r.json()
    assert p["accepted"] is True
    assert p["scenario_count"] == 4

def test_action_playground_run():
    r = client.post("/action-playground/run")
    assert r.status_code == 200
    assert r.json()["accepted"] is True

def test_action_playground_run_all():
    r = client.post("/action-playground/run-all")
    assert r.status_code == 200
    assert r.json()["accepted"] is True

def test_action_playground_report():
    r = client.get("/action-playground/report")
    assert r.status_code == 200
    assert r.json()["accepted"] is True

def test_action_playground_openapi_routes():
    r = client.get("/openapi.json")
    paths = r.json()["paths"]
    assert "/action-playground/scenarios" in paths
    assert "/action-playground/run" in paths
    assert "/action-playground/run-all" in paths
    assert "/action-playground/report" in paths
