"""Tests for the FastAPI dashboard API layer."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


@pytest.fixture
def client():
    from oura_fun.api.app import app
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_people_empty(client):
    with patch("oura_fun.api.app.db.list_people", return_value=[]):
        r = client.get("/api/people")
    assert r.status_code == 200
    assert r.json() == {"people": []}


def test_people_returns_list(client):
    with patch("oura_fun.api.app.db.list_people", return_value=["alice", "bob"]):
        r = client.get("/api/people")
    assert r.json()["people"] == ["alice", "bob"]


def test_sleep_endpoint(client):
    fake = [{"day": "2024-01-01", "score": 85, "total_sleep_duration": 28800}]
    with patch("oura_fun.api.app.db.get_sleep", return_value=fake) as m:
        r = client.get("/api/sleep/alice?start=2024-01-01&end=2024-01-31")
    assert r.status_code == 200
    data = r.json()
    assert data["person_id"] == "alice"
    assert data["records"] == fake
    m.assert_called_once_with("alice", "2024-01-01", "2024-01-31")


def test_readiness_endpoint(client):
    fake = [{"day": "2024-01-01", "score": 72}]
    with patch("oura_fun.api.app.db.get_readiness", return_value=fake):
        r = client.get("/api/readiness/alice")
    assert r.status_code == 200
    assert r.json()["records"] == fake


def test_activity_endpoint(client):
    fake = [{"day": "2024-01-01", "score": 90, "steps": 12000}]
    with patch("oura_fun.api.app.db.get_activity", return_value=fake):
        r = client.get("/api/activity/alice")
    assert r.status_code == 200
    assert r.json()["records"] == fake


def test_compare_endpoint(client):
    with (
        patch("oura_fun.api.app.db.list_people", return_value=["alice"]),
        patch("oura_fun.api.app.db.get_readiness", return_value=[{"day": "2024-01-01", "score": 80}]),
    ):
        r = client.get("/api/compare?metric=readiness")
    assert r.status_code == 200
    data = r.json()
    assert data["metric"] == "readiness"
    assert "alice" in data["people"]


def test_compare_unknown_metric(client):
    r = client.get("/api/compare?metric=stress")
    assert r.status_code == 200
    assert "error" in r.json()


def test_date_window_defaults(client):
    """Default window is 30 days ending today."""
    with patch("oura_fun.api.app.db.get_sleep", return_value=[]) as m:
        r = client.get("/api/sleep/alice")
    assert r.status_code == 200
    body = r.json()
    from datetime import date, timedelta
    assert body["end"] == str(date.today())
    assert body["start"] == str(date.today() - timedelta(days=30))
