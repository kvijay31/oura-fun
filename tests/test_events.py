"""Tests for F1.4: events & metadata endpoint wrappers and Pydantic models."""

from __future__ import annotations

import respx
import httpx
import pytest

from oura_fun.client import OuraClient, BASE_URL
from oura_fun.events import (
    fetch_enhanced_tag,
    fetch_personal_info,
    fetch_session,
    fetch_workout,
)
from oura_fun.models import EnhancedTag, PersonalInfo, Session, Workout


TOKEN = "test_token"


def _client() -> OuraClient:
    return OuraClient(TOKEN)


def _mock_list(endpoint: str, data: list[dict]) -> None:
    respx.get(f"{BASE_URL}/{endpoint}").mock(
        return_value=httpx.Response(200, json={"data": data, "next_token": None})
    )


def _mock_single(endpoint: str, data: dict) -> None:
    respx.get(f"{BASE_URL}/{endpoint}").mock(
        return_value=httpx.Response(200, json=data)
    )


# ── workout ───────────────────────────────────────────────────────────────────

@respx.mock
def test_fetch_workout_returns_models():
    _mock_list("workout", [
        {
            "id": "w1",
            "day": "2024-01-01",
            "start_datetime": "2024-01-01T08:00:00+00:00",
            "end_datetime": "2024-01-01T09:00:00+00:00",
            "activity": "running",
            "calories": 450.0,
            "distance": 5200.0,
            "intensity": "moderate",
            "label": None,
            "source": "manual",
        }
    ])
    with _client() as c:
        results = fetch_workout(c, "2024-01-01", "2024-01-01")
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, Workout)
    assert r.id == "w1"
    assert r.activity == "running"
    assert r.calories == pytest.approx(450.0)
    assert r.distance == pytest.approx(5200.0)
    assert r.intensity == "moderate"
    assert r.source == "manual"


@respx.mock
def test_fetch_workout_optional_fields_none():
    _mock_list("workout", [{"id": "w2", "day": "2024-01-02"}])
    with _client() as c:
        results = fetch_workout(c, "2024-01-02", "2024-01-02")
    r = results[0]
    assert r.activity is None
    assert r.calories is None
    assert r.label is None


@respx.mock
def test_fetch_workout_empty_response():
    _mock_list("workout", [])
    with _client() as c:
        results = fetch_workout(c, "2024-01-01", "2024-01-31")
    assert results == []


# ── session ───────────────────────────────────────────────────────────────────

@respx.mock
def test_fetch_session_returns_models():
    _mock_list("session", [
        {
            "id": "ses1",
            "day": "2024-01-01",
            "start_datetime": "2024-01-01T20:00:00+00:00",
            "end_datetime": "2024-01-01T20:30:00+00:00",
            "type": "meditation",
            "heart_rate": {
                "interval": 5,
                "items": [60.0, 62.0, 61.0],
                "timestamp": "2024-01-01T20:00:00+00:00",
            },
            "heart_rate_variance": {
                "interval": 5,
                "items": [25.0, 26.0, 24.5],
                "timestamp": "2024-01-01T20:00:00+00:00",
            },
            "mood": "good",
            "perceived_exertion": 2.0,
        }
    ])
    with _client() as c:
        results = fetch_session(c, "2024-01-01", "2024-01-01")
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, Session)
    assert r.type == "meditation"
    assert r.mood == "good"
    assert r.perceived_exertion == pytest.approx(2.0)
    assert r.heart_rate.interval == pytest.approx(5.0)
    assert r.heart_rate.items == [60.0, 62.0, 61.0]
    assert r.heart_rate_variance.items[0] == pytest.approx(25.0)


@respx.mock
def test_fetch_session_optional_fields_none():
    _mock_list("session", [{"id": "ses2", "day": "2024-01-02"}])
    with _client() as c:
        results = fetch_session(c, "2024-01-02", "2024-01-02")
    r = results[0]
    assert r.type is None
    assert r.heart_rate is None
    assert r.mood is None


@respx.mock
def test_fetch_session_null_items_in_timeseries():
    _mock_list("session", [
        {
            "id": "ses3",
            "day": "2024-01-03",
            "heart_rate": {"interval": 5, "items": [60.0, None, 62.0], "timestamp": "..."},
        }
    ])
    with _client() as c:
        results = fetch_session(c, "2024-01-03", "2024-01-03")
    assert results[0].heart_rate.items[1] is None


# ── enhanced_tag ──────────────────────────────────────────────────────────────

@respx.mock
def test_fetch_enhanced_tag_returns_models():
    _mock_list("enhanced_tag", [
        {
            "id": "et1",
            "tag_type_code": "tag_generic_tag",
            "start_time": "2024-01-01T20:00:00+00:00",
            "end_time": None,
            "start_day": "2024-01-01",
            "end_day": None,
            "comment": "Felt great today",
            "custom_name": None,
        }
    ])
    with _client() as c:
        results = fetch_enhanced_tag(c, "2024-01-01", "2024-01-01")
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, EnhancedTag)
    assert r.tag_type_code == "tag_generic_tag"
    assert r.comment == "Felt great today"
    assert r.end_time is None


@respx.mock
def test_fetch_enhanced_tag_custom_name():
    _mock_list("enhanced_tag", [
        {
            "id": "et2",
            "day": "2024-01-02",
            "tag_type_code": "tag_custom",
            "start_time": "2024-01-02T10:00:00+00:00",
            "start_day": "2024-01-02",
            "custom_name": "My Custom Tag",
        }
    ])
    with _client() as c:
        results = fetch_enhanced_tag(c, "2024-01-02", "2024-01-02")
    assert results[0].custom_name == "My Custom Tag"


@respx.mock
def test_fetch_enhanced_tag_empty():
    _mock_list("enhanced_tag", [])
    with _client() as c:
        results = fetch_enhanced_tag(c, "2024-01-01", "2024-01-31")
    assert results == []


# ── personal_info ─────────────────────────────────────────────────────────────

@respx.mock
def test_fetch_personal_info_returns_model():
    _mock_single("personal_info", {
        "id": "pi1",
        "age": 32,
        "weight": 75.5,
        "height": 1.80,
        "biological_sex": "male",
        "email": "user@example.com",
    })
    with _client() as c:
        result = fetch_personal_info(c)
    assert isinstance(result, PersonalInfo)
    assert result.id == "pi1"
    assert result.age == 32
    assert result.weight == pytest.approx(75.5)
    assert result.biological_sex == "male"
    assert result.email == "user@example.com"


@respx.mock
def test_fetch_personal_info_optional_fields_none():
    _mock_single("personal_info", {"id": "pi2"})
    with _client() as c:
        result = fetch_personal_info(c)
    assert result.age is None
    assert result.email is None


# ── extra fields are tolerated ────────────────────────────────────────────────

@respx.mock
def test_workout_unknown_fields_ignored():
    _mock_list("workout", [
        {"id": "w9", "day": "2024-01-09", "activity": "yoga", "future_field": "x"}
    ])
    with _client() as c:
        results = fetch_workout(c, "2024-01-09", "2024-01-09")
    assert results[0].activity == "yoga"
