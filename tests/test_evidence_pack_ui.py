from __future__ import annotations

from fastapi.testclient import TestClient

from omega_runtime.api import app


client = TestClient(app)


def test_evidence_pack_ui_page_exists():
    response = client.get("/evidence-pack")

    assert response.status_code == 200
    assert "OMEGA Evidence Pack UI" in response.text
    assert "Run evidence pack" in response.text
    assert "/evidence-pack/run" in response.text
    assert "/evidence-pack/report" in response.text


def test_evidence_pack_ui_alias_exists():
    response = client.get("/ui/evidence-pack")

    assert response.status_code == 200
    assert "Export proof, trace, and failure evidence" in response.text


def test_evidence_pack_report_endpoint_shape():
    response = client.get("/evidence-pack/report")

    assert response.status_code == 200

    payload = response.json()

    assert "accepted" in payload
    assert "reason" in payload
    assert payload["evidence_pack_ui_version"] == "OMEGA_EVIDENCE_PACK_UI_V1"
    assert "report_path" in payload
    assert "report_exists" in payload


def test_evidence_pack_routes_are_in_openapi():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert "/evidence-pack/run" in paths
    assert "post" in paths["/evidence-pack/run"]

    assert "/evidence-pack/report" in paths
    assert "get" in paths["/evidence-pack/report"]
