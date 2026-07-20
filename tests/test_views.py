"""Tests for F2.2: derived DuckDB views."""

from __future__ import annotations

import json
from datetime import date, datetime

import duckdb
import pytest

from oura_fun.db import init_db
from oura_fun.views import VIEW_NAMES


@pytest.fixture()
def conn():
    c = duckdb.connect(":memory:")
    init_db(c)
    yield c
    c.close()


T1 = datetime(2024, 1, 16, 8, 0, 0)
T2 = datetime(2024, 1, 16, 9, 0, 0)


def _row(table: str, conn: duckdb.DuckDBPyConnection, person: str, key: str, day: str, payload: dict, ts: datetime) -> None:
    conn.execute(
        f"INSERT INTO {table} VALUES (?, ?, ?, ?, ?)",
        [person, key, day, json.dumps(payload), ts],
    )


# ── view creation ─────────────────────────────────────────────────────────────

def test_all_views_exist(conn):
    existing = {
        r[0]
        for r in conn.execute(
            "SELECT table_name FROM information_schema.views WHERE table_schema = 'main'"
        ).fetchall()
    }
    for name in VIEW_NAMES:
        assert name in existing, f"Missing view: {name}"


# ── dedup: latest fetched_at wins ─────────────────────────────────────────────

def test_v_sleep_nightly_dedup_latest_wins(conn):
    _row("raw_daily_sleep", conn, "p1", "s1", "2024-01-15",
         {"id": "s1", "day": "2024-01-15", "score": 78}, T1)
    _row("raw_daily_sleep", conn, "p1", "s1", "2024-01-15",
         {"id": "s1", "day": "2024-01-15", "score": 85}, T2)

    rows = conn.execute("SELECT score FROM v_sleep_nightly").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == 85


def test_v_readiness_daily_dedup_latest_wins(conn):
    _row("raw_daily_readiness", conn, "p1", "r1", "2024-01-15",
         {"id": "r1", "day": "2024-01-15", "score": 70}, T1)
    _row("raw_daily_readiness", conn, "p1", "r1", "2024-01-15",
         {"id": "r1", "day": "2024-01-15", "score": 80}, T2)

    rows = conn.execute("SELECT score FROM v_readiness_daily").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == 80


def test_v_activity_daily_dedup_latest_wins(conn):
    _row("raw_daily_activity", conn, "p1", "a1", "2024-01-15",
         {"id": "a1", "day": "2024-01-15", "steps": 5000}, T1)
    _row("raw_daily_activity", conn, "p1", "a1", "2024-01-15",
         {"id": "a1", "day": "2024-01-15", "steps": 8000}, T2)

    rows = conn.execute("SELECT steps FROM v_activity_daily").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == 8000


# ── different keys are not merged ─────────────────────────────────────────────

def test_v_sleep_nightly_multiple_days(conn):
    _row("raw_daily_sleep", conn, "p1", "s1", "2024-01-14", {"id": "s1", "day": "2024-01-14", "score": 70}, T1)
    _row("raw_daily_sleep", conn, "p1", "s2", "2024-01-15", {"id": "s2", "day": "2024-01-15", "score": 80}, T1)

    rows = conn.execute("SELECT score FROM v_sleep_nightly ORDER BY score").fetchall()
    assert len(rows) == 2
    assert rows[0][0] == 70
    assert rows[1][0] == 80


def test_v_sleep_nightly_multiple_people(conn):
    _row("raw_daily_sleep", conn, "p1", "s1", "2024-01-15", {"id": "s1", "score": 75}, T1)
    _row("raw_daily_sleep", conn, "p2", "s2", "2024-01-15", {"id": "s2", "score": 90}, T1)

    rows = conn.execute("SELECT person_id, score FROM v_sleep_nightly ORDER BY person_id").fetchall()
    assert len(rows) == 2
    assert rows[0] == ("p1", 75)
    assert rows[1] == ("p2", 90)


# ── JSON flattening ───────────────────────────────────────────────────────────

def test_v_sleep_nightly_contributors(conn):
    payload = {
        "id": "s1", "day": "2024-01-15", "score": 82,
        "contributors": {"deep_sleep": 90, "efficiency": 85, "rem_sleep": 70, "restfulness": 88},
    }
    _row("raw_daily_sleep", conn, "p1", "s1", "2024-01-15", payload, T1)

    row = conn.execute(
        "SELECT score, c_deep_sleep, c_efficiency, c_rem_sleep, c_restfulness FROM v_sleep_nightly"
    ).fetchone()
    assert row == (82, 90, 85, 70, 88)


def test_v_readiness_daily_temperature_and_contributors(conn):
    payload = {
        "id": "r1", "day": "2024-01-15", "score": 90,
        "temperature_deviation": 0.25,
        "contributors": {"hrv_balance": 88, "resting_heart_rate": 92},
    }
    _row("raw_daily_readiness", conn, "p1", "r1", "2024-01-15", payload, T1)

    row = conn.execute(
        "SELECT score, temperature_deviation, c_hrv_balance, c_resting_heart_rate FROM v_readiness_daily"
    ).fetchone()
    assert row == (90, 0.25, 88, 92)


def test_v_activity_daily_fields(conn):
    payload = {
        "id": "a1", "day": "2024-01-15", "score": 75,
        "steps": 9500, "active_calories": 350, "total_calories": 2200,
        "contributors": {"stay_active": 80, "training_volume": 65},
    }
    _row("raw_daily_activity", conn, "p1", "a1", "2024-01-15", payload, T1)

    row = conn.execute(
        "SELECT score, steps, active_calories, total_calories, c_stay_active, c_training_volume FROM v_activity_daily"
    ).fetchone()
    assert row == (75, 9500, 350, 2200, 80, 65)


def test_v_stress_daily_fields(conn):
    payload = {"id": "st1", "day": "2024-01-15", "stress_high": 40, "recovery_high": 60, "day_summary": "restored"}
    _row("raw_daily_stress", conn, "p1", "st1", "2024-01-15", payload, T1)

    row = conn.execute("SELECT stress_high, recovery_high, day_summary FROM v_stress_daily").fetchone()
    assert row == (40, 60, "restored")


def test_v_spo2_daily_average(conn):
    payload = {"id": "o1", "day": "2024-01-15", "spo2_percentage": {"average": 97.5}}
    _row("raw_daily_spo2", conn, "p1", "o1", "2024-01-15", payload, T1)

    row = conn.execute("SELECT spo2_avg FROM v_spo2_daily").fetchone()
    assert row[0] == pytest.approx(97.5)


def test_v_sleep_period_fields(conn):
    payload = {
        "id": "sp1", "day": "2024-01-15", "type": "long_sleep",
        "average_hrv": 45, "deep_sleep_duration": 3600, "total_sleep_duration": 25200,
    }
    _row("raw_sleep", conn, "p1", "sp1", "2024-01-15", payload, T1)

    row = conn.execute("SELECT type, average_hrv, deep_sleep_duration, total_sleep_duration FROM v_sleep_period").fetchone()
    assert row == ("long_sleep", 45, 3600, 25200)


def test_v_sleep_time_fields(conn):
    payload = {
        "id": "slt1", "day": "2024-01-15", "recommendation": "earlier",
        "status": "optimal", "optimal_bedtime": {"day_tz": -18000, "start_offset": -3600, "end_offset": 0},
    }
    _row("raw_sleep_time", conn, "p1", "slt1", "2024-01-15", payload, T1)

    row = conn.execute("SELECT recommendation, status, bedtime_start_offset, bedtime_end_offset FROM v_sleep_time").fetchone()
    assert row == ("earlier", "optimal", -3600, 0)


def test_v_heartrate_fields(conn):
    payload = {"bpm": 62, "source": "awake", "timestamp": "2024-01-15T08:00:00+00:00"}
    _row("raw_heartrate", conn, "p1", "2024-01-15T08:00:00+00:00", "2024-01-15", payload, T1)

    row = conn.execute("SELECT bpm, source FROM v_heartrate").fetchone()
    assert row == (62, "awake")


def test_v_workout_fields(conn):
    payload = {"id": "w1", "day": "2024-01-15", "activity": "running", "calories": 450.0, "distance": 5000.0}
    _row("raw_workout", conn, "p1", "w1", "2024-01-15", payload, T1)

    row = conn.execute("SELECT activity, calories, distance FROM v_workout").fetchone()
    assert row == ("running", 450.0, 5000.0)


def test_v_enhanced_tag_fields(conn):
    payload = {"id": "et1", "tag_type_code": "tag_alcohol", "start_day": "2024-01-15", "comment": "one glass"}
    _row("raw_enhanced_tag", conn, "p1", "et1", "2024-01-15", payload, T1)

    row = conn.execute("SELECT tag_type_code, start_day, comment FROM v_enhanced_tag").fetchone()
    assert row == ("tag_alcohol", "2024-01-15", "one glass")


def test_v_personal_info_fields(conn):
    payload = {"id": "pi1", "age": 30, "weight": 70.5, "height": 1.78, "biological_sex": "male", "email": "a@b.com"}
    _row("raw_personal_info", conn, "p1", "personal_info", "2024-01-15", payload, T1)

    row = conn.execute("SELECT age, weight, height, biological_sex, email FROM v_personal_info").fetchone()
    assert row == (30, 70.5, 1.78, "male", "a@b.com")


# ── null tolerance ────────────────────────────────────────────────────────────

def test_v_sleep_nightly_missing_optional_fields_are_null(conn):
    _row("raw_daily_sleep", conn, "p1", "s1", "2024-01-15", {"id": "s1", "day": "2024-01-15"}, T1)

    row = conn.execute("SELECT score, c_deep_sleep, c_efficiency FROM v_sleep_nightly").fetchone()
    assert row == (None, None, None)
