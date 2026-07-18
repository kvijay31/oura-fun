"""Tests for F1.2: daily metric endpoint wrappers and Pydantic models."""

from __future__ import annotations

import respx
import httpx
import pytest

from oura_fun.client import OuraClient, BASE_URL
from oura_fun.daily import (
    fetch_daily_activity,
    fetch_daily_readiness,
    fetch_daily_sleep,
    fetch_daily_spo2,
    fetch_daily_stress,
    fetch_sleep_time,
)
from oura_fun.models import (
    DailyActivity,
    DailyReadiness,
    DailySleep,
    DailySpo2,
    DailyStress,
    SleepTime,
)


TOKEN = "test_token"


def _client() -> OuraClient:
    return OuraClient(TOKEN)


def _mock(endpoint: str, data: list[dict]) -> None:
    respx.get(f"{BASE_URL}/{endpoint}").mock(
        return_value=httpx.Response(200, json={"data": data, "next_token": None})
    )


# ── daily_sleep ───────────────────────────────────────────────────────────────

@respx.mock
def test_fetch_daily_sleep_returns_models():
    _mock("daily_sleep", [
        {"id": "s1", "day": "2024-01-01", "score": 82,
         "contributors": {"deep_sleep": 90, "total_sleep": 85}},
    ])
    with _client() as c:
        results = fetch_daily_sleep(c, "2024-01-01", "2024-01-01")
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, DailySleep)
    assert r.id == "s1"
    assert r.score == 82
    assert r.contributors.deep_sleep == 90


@respx.mock
def test_fetch_daily_sleep_optional_fields_none():
    _mock("daily_sleep", [{"id": "s2", "day": "2024-01-02"}])
    with _client() as c:
        results = fetch_daily_sleep(c, "2024-01-02", "2024-01-02")
    assert results[0].score is None
    assert results[0].contributors is None


# ── daily_readiness ───────────────────────────────────────────────────────────

@respx.mock
def test_fetch_daily_readiness_returns_models():
    _mock("daily_readiness", [
        {"id": "r1", "day": "2024-01-01", "score": 75,
         "temperature_deviation": 0.1,
         "contributors": {"hrv_balance": 80, "resting_heart_rate": 70}},
    ])
    with _client() as c:
        results = fetch_daily_readiness(c, "2024-01-01", "2024-01-01")
    r = results[0]
    assert isinstance(r, DailyReadiness)
    assert r.score == 75
    assert r.temperature_deviation == pytest.approx(0.1)
    assert r.contributors.hrv_balance == 80


# ── daily_activity ────────────────────────────────────────────────────────────

@respx.mock
def test_fetch_daily_activity_returns_models():
    _mock("daily_activity", [
        {"id": "a1", "day": "2024-01-01", "score": 90,
         "steps": 12000, "active_calories": 500,
         "contributors": {"meet_daily_targets": 95}},
    ])
    with _client() as c:
        results = fetch_daily_activity(c, "2024-01-01", "2024-01-01")
    r = results[0]
    assert isinstance(r, DailyActivity)
    assert r.steps == 12000
    assert r.active_calories == 500
    assert r.contributors.meet_daily_targets == 95


# ── daily_stress ──────────────────────────────────────────────────────────────

@respx.mock
def test_fetch_daily_stress_returns_models():
    _mock("daily_stress", [
        {"id": "st1", "day": "2024-01-01", "stress_high": 3600,
         "recovery_high": 7200, "day_summary": "normal"},
    ])
    with _client() as c:
        results = fetch_daily_stress(c, "2024-01-01", "2024-01-01")
    r = results[0]
    assert isinstance(r, DailyStress)
    assert r.stress_high == 3600
    assert r.day_summary == "normal"


@respx.mock
def test_fetch_daily_stress_nullable_fields():
    _mock("daily_stress", [{"id": "st2", "day": "2024-01-02"}])
    with _client() as c:
        results = fetch_daily_stress(c, "2024-01-02", "2024-01-02")
    r = results[0]
    assert r.stress_high is None
    assert r.day_summary is None


# ── daily_spo2 ────────────────────────────────────────────────────────────────

@respx.mock
def test_fetch_daily_spo2_returns_models():
    _mock("daily_spo2", [
        {"id": "sp1", "day": "2024-01-01",
         "spo2_percentage": {"average": 97.5}},
    ])
    with _client() as c:
        results = fetch_daily_spo2(c, "2024-01-01", "2024-01-01")
    r = results[0]
    assert isinstance(r, DailySpo2)
    assert r.spo2_percentage.average == pytest.approx(97.5)


@respx.mock
def test_fetch_daily_spo2_no_percentage():
    _mock("daily_spo2", [{"id": "sp2", "day": "2024-01-02", "spo2_percentage": None}])
    with _client() as c:
        results = fetch_daily_spo2(c, "2024-01-02", "2024-01-02")
    assert results[0].spo2_percentage is None


# ── sleep_time ────────────────────────────────────────────────────────────────

@respx.mock
def test_fetch_sleep_time_returns_models():
    _mock("sleep_time", [
        {"id": "t1", "day": "2024-01-01",
         "optimal_bedtime": {"day_tz": -300, "end_offset": 30, "start_offset": -60},
         "recommendation": "standard", "status": "good_nights"},
    ])
    with _client() as c:
        results = fetch_sleep_time(c, "2024-01-01", "2024-01-01")
    r = results[0]
    assert isinstance(r, SleepTime)
    assert r.recommendation == "standard"
    assert r.optimal_bedtime.end_offset == 30


@respx.mock
def test_fetch_sleep_time_empty_response():
    _mock("sleep_time", [])
    with _client() as c:
        results = fetch_sleep_time(c, "2024-01-01", "2024-01-31")
    assert results == []


# ── extra fields are tolerated (Oura may add fields) ─────────────────────────

@respx.mock
def test_unknown_fields_ignored():
    _mock("daily_sleep", [
        {"id": "s3", "day": "2024-01-03", "score": 70,
         "future_field": "some_value", "another_new": 123},
    ])
    with _client() as c:
        results = fetch_daily_sleep(c, "2024-01-03", "2024-01-03")
    assert results[0].id == "s3"
