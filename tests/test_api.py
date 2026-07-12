"""Tests for the FastAPI layer using TestClient."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import incident_agent.store as store_module
from incident_agent.main import create_app


@pytest.fixture(autouse=True)
def _reset_report_store():
    # The report store is a module-level singleton; reset it so tests that
    # list/count reports aren't affected by reports saved in other tests.
    store_module._store = None
    yield
    store_module._store = None


@pytest.fixture
def client():
    return TestClient(create_app())


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["mock_mode"] is True
    assert body["llm_provider"] == "mock"


def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["investigate"] == "POST /investigate"


def test_investigate_endpoint(client):
    resp = client.post(
        "/investigate",
        json={
            "title": "Production API latency increased to 8 seconds",
            "description": "Checkout API is slow",
            "severity": "critical",
            "service": "api",
        },
    )
    assert resp.status_code == 200
    report = resp.json()
    assert report["root_cause"]["recommended_action"] == "rollback"
    assert report["evidence"]
    assert report["approved"] is False
    assert report["id"].startswith("rpt_")


def test_get_report_roundtrip(client):
    created = client.post(
        "/investigate", json={"title": "latency spike", "service": "api"}
    ).json()
    report_id = created["id"]

    fetched = client.get(f"/reports/{report_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == report_id


def test_get_report_404(client):
    resp = client.get("/reports/does-not-exist")
    assert resp.status_code == 404


def test_approval_flow(client):
    created = client.post(
        "/investigate", json={"title": "latency spike", "service": "api"}
    ).json()
    report_id = created["id"]

    resp = client.post(
        f"/reports/{report_id}/approval",
        json={"approved": True, "note": "rolling back now"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["approved"] is True
    assert any("approved" in line for line in body["timeline"])


def test_list_reports_empty(client):
    resp = client.get("/reports")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"total": 0, "limit": 20, "offset": 0, "items": []}


def test_list_reports_returns_created_reports_newest_first(client):
    first = client.post("/investigate", json={"title": "incident one"}).json()
    second = client.post("/investigate", json={"title": "incident two"}).json()

    resp = client.get("/reports")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    ids_in_order = [item["id"] for item in body["items"]]
    assert ids_in_order == [second["id"], first["id"]]
    assert body["items"][0]["incident_title"] == "incident two"


def test_list_reports_pagination(client):
    for i in range(5):
        client.post("/investigate", json={"title": f"incident {i}"})

    resp = client.get("/reports", params={"limit": 2, "offset": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 5
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert len(body["items"]) == 2


def test_list_reports_rejects_invalid_limit(client):
    resp = client.get("/reports", params={"limit": 0})
    assert resp.status_code == 422
