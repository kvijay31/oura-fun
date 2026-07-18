"""Tests for the F9.2 FastAPI backend layer.

Uses an in-process temporary DuckDB file with real raw tables so tests
exercise the actual view SQL and query logic, not mocked data.
"""
from __future__ import annotations

import json
from datetime import date, datetime

import duckdb
import pytest
from fastapi.testclient import TestClient

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS {table} (
    person_id   TEXT      NOT NULL,
    natural_key TEXT      NOT NULL,
    day         DATE      NOT NULL,
    payload     JSON      NOT NULL,
    fetched_at  TIMESTAMP NOT NULL,
    PRIMARY KEY (person_id, natural_key, day, fetched_at)
)"""

_SLEEP_PAYLOAD = {
    "id": "s1",
    "score": 82,
    "contributors": {
        "deep_sleep": 75,
        "efficiency": 90,
        "latency": 88,
        "rem_sleep": 79,
        "restfulness": 83,
        "timing": 85,
        "total_sleep": 80,
    },
    "day": "2024-01-15",
    "timestamp": "2024-01-15T00:00:00+00:00",
}

_READINESS_PAYLOAD = {
    "id": "r1",
    "score": 74,
    "temperature_deviation": 0.12,
    "temperature_trend_deviation": 0.05,
    "contributors": {
        "activity_balance": 60,
        "body_temperature": 95,
        "hrv_balance": 70,
        "previous_day_activity": 80,
        "previous_night": 75,
        "recovery_index": 65,
        "resting_heart_rate": 90,
        "sleep_balance": 78,
    },
    "day": "2024-01-15",
    "timestamp": "2024-01-15T00:00:00+00:00",
}

_ACTIVITY_PAYLOAD = {
    "id": "a1",
    "score": 88,
    "active_calories": 450,
    "steps": 8200,
    "equivalent_walking_distance": 6500,
    "high_activity_time": 900,
    "medium_activity_time": 3600,
    "low_activity_time": 14400,
    "non_wear_time": 0,
    "inactivity_alerts": 2,
    "total_calories": 2200,
    "contributors": {
        "meet_daily_targets": 55,
        "move_every_hour": 100,
        "recovery_time": 95,
        "stay_active": 88,
        "training_frequency": 72,
        "training_volume": 68,
    },
    "day": "2024-01-15",
    "timestamp": "2024-01-15T04:00:00-05:00",
}


def _make_db(path: str) -> None:
    conn = duckdb.connect(path)
    for table in ("raw_daily_sleep", "raw_daily_readiness", "raw_daily_activity"):
        conn.execute(_CREATE_TABLE.format(table=table))

    ts = datetime(2024, 1, 15, 10, 0, 0)
    # alice data
    conn.execute(
        "INSERT INTO raw_daily_sleep VALUES (?,?,?,?,?)",
        ["alice", "s1", date(2024, 1, 15), json.dumps(_SLEEP_PAYLOAD), ts],
    )
    conn.execute(
        "INSERT INTO raw_daily_readiness VALUES (?,?,?,?,?)",
        ["alice", "r1", date(2024, 1, 15), json.dumps(_READINESS_PAYLOAD), ts],
    )
    conn.execute(
        "INSERT INTO raw_daily_activity VALUES (?,?,?,?,?)",
        ["alice", "a1", date(2024, 1, 15), json.dumps(_ACTIVITY_PAYLOAD), ts],
    )
    # bob sleep — ensures person_id scoping works
    bob_payload = {**_SLEEP_PAYLOAD, "id": "s2", "score": 60}
    conn.execute(
        "INSERT INTO raw_daily_sleep VALUES (?,?,?,?,?)",
        ["bob", "s2", date(2024, 1, 15), json.dumps(bob_payload), ts],
    )
    # alice — second fetch of the same day (should deduplicate to latest)
    updated_payload = {**_SLEEP_PAYLOAD, "score": 85}
    conn.execute(
        "INSERT INTO raw_daily_sleep VALUES (?,?,?,?,?)",
        ["alice", "s1", date(2024, 1, 15), json.dumps(updated_payload), datetime(2024, 1, 15, 11, 0, 0)],
    )
    conn.close()


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.duckdb")
    _make_db(db_path)
    monkeypatch.setenv("OURA_DB_PATH", db_path)

    # Reset module-level state so each test gets a fresh init
    import oura_fun.api.db as db_mod
    db_mod._db_path = None

    from oura_fun.api.app import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client_no_db(tmp_path, monkeypatch):
    monkeypatch.setenv("OURA_DB_PATH", str(tmp_path / "missing.duckdb"))
    import oura_fun.api.db as db_mod
    db_mod._db_path = None
    from oura_fun.api.app import app
    with TestClient(app) as c:
        yield c


class TestHealthz:
    def test_healthz_ok(self, client):
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestNoDb:
    def test_sleep_503_without_db(self, client_no_db):
        r = client_no_db.get("/api/v1/sleep", params={"person_id": "alice", "start": "2024-01-01"})
        assert r.status_code == 503

    def test_readiness_503_without_db(self, client_no_db):
        r = client_no_db.get("/api/v1/readiness", params={"person_id": "alice", "start": "2024-01-01"})
        assert r.status_code == 503

    def test_activity_503_without_db(self, client_no_db):
        r = client_no_db.get("/api/v1/activity", params={"person_id": "alice", "start": "2024-01-01"})
        assert r.status_code == 503

    def test_people_503_without_db(self, client_no_db):
        r = client_no_db.get("/api/v1/people")
        assert r.status_code == 503


class TestSleep:
    def test_returns_record(self, client):
        r = client.get("/api/v1/sleep", params={"person_id": "alice", "start": "2024-01-15", "end": "2024-01-15"})
        assert r.status_code == 200
        body = r.json()
        assert body["person_id"] == "alice"
        assert len(body["records"]) == 1

    def test_deduplicates_to_latest_fetch(self, client):
        """Two fetches for the same day → view returns the latest score (85, not 82)."""
        r = client.get("/api/v1/sleep", params={"person_id": "alice", "start": "2024-01-15", "end": "2024-01-15"})
        rec = r.json()["records"][0]
        assert rec["score"] == 85

    def test_contributors_present(self, client):
        r = client.get("/api/v1/sleep", params={"person_id": "alice", "start": "2024-01-15", "end": "2024-01-15"})
        contrib = r.json()["records"][0]["contributors"]
        assert contrib is not None
        assert contrib["deep_sleep"] == 75
        assert contrib["efficiency"] == 90

    def test_person_id_scoping(self, client):
        """Alice query must not include bob's record."""
        r = client.get("/api/v1/sleep", params={"person_id": "alice", "start": "2024-01-15", "end": "2024-01-15"})
        assert len(r.json()["records"]) == 1
        assert r.json()["records"][0]["score"] != 60  # bob's score

    def test_empty_when_out_of_range(self, client):
        r = client.get("/api/v1/sleep", params={"person_id": "alice", "start": "2023-01-01", "end": "2023-12-31"})
        assert r.status_code == 200
        assert r.json()["records"] == []

    def test_missing_person_returns_empty(self, client):
        r = client.get("/api/v1/sleep", params={"person_id": "nobody", "start": "2024-01-15", "end": "2024-01-15"})
        assert r.status_code == 200
        assert r.json()["records"] == []


class TestReadiness:
    def test_returns_record_with_score(self, client):
        r = client.get("/api/v1/readiness", params={"person_id": "alice", "start": "2024-01-15", "end": "2024-01-15"})
        assert r.status_code == 200
        rec = r.json()["records"][0]
        assert rec["score"] == 74

    def test_temperature_fields(self, client):
        r = client.get("/api/v1/readiness", params={"person_id": "alice", "start": "2024-01-15", "end": "2024-01-15"})
        rec = r.json()["records"][0]
        assert abs(rec["temperature_deviation"] - 0.12) < 1e-6

    def test_contributors(self, client):
        r = client.get("/api/v1/readiness", params={"person_id": "alice", "start": "2024-01-15", "end": "2024-01-15"})
        contrib = r.json()["records"][0]["contributors"]
        assert contrib["hrv_balance"] == 70


class TestActivity:
    def test_returns_record_with_quantitative_data(self, client):
        r = client.get("/api/v1/activity", params={"person_id": "alice", "start": "2024-01-15", "end": "2024-01-15"})
        assert r.status_code == 200
        rec = r.json()["records"][0]
        assert rec["score"] == 88
        assert rec["steps"] == 8200
        assert rec["active_calories"] == 450

    def test_contributors(self, client):
        r = client.get("/api/v1/activity", params={"person_id": "alice", "start": "2024-01-15", "end": "2024-01-15"})
        contrib = r.json()["records"][0]["contributors"]
        assert contrib["move_every_hour"] == 100
        assert contrib["stay_active"] == 88


class TestPeople:
    def test_lists_all_people(self, client):
        r = client.get("/api/v1/people")
        assert r.status_code == 200
        people = r.json()["people"]
        assert "alice" in people
        assert "bob" in people

    def test_sorted(self, client):
        r = client.get("/api/v1/people")
        people = r.json()["people"]
        assert people == sorted(people)
