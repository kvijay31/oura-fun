"""Tests for F9.5 access-control model."""

import pytest
from unittest.mock import patch

from oura_fun.api.access import Role, get_role, filter_records


# ---------------------------------------------------------------------------
# get_role
# ---------------------------------------------------------------------------

def test_no_viewer_is_owner():
    """Absent viewer_id → OWNER (trusted local browser)."""
    assert get_role(None, "alice") is Role.OWNER


def test_viewer_equals_subject_is_owner():
    """You always see your own full data."""
    assert get_role("alice", "alice") is Role.OWNER


def test_viewer_equals_subject_case_insensitive():
    assert get_role("Alice", "alice") is Role.OWNER


def test_viewer_in_owners_is_owner():
    with patch.dict("os.environ", {"OURA_OWNERS": "alice,bob"}):
        assert get_role("alice", "charlie") is Role.OWNER
        assert get_role("bob", "charlie") is Role.OWNER


def test_viewer_not_in_owners_is_friend():
    with patch.dict("os.environ", {"OURA_OWNERS": "alice,bob"}):
        assert get_role("charlie", "alice") is Role.FRIEND


def test_no_owners_env_means_all_owner():
    """OURA_OWNERS unset → local all-access mode, any viewer gets OWNER."""
    with patch.dict("os.environ", {}, clear=True):
        assert get_role("stranger", "alice") is Role.OWNER


def test_empty_owners_env_means_all_owner():
    with patch.dict("os.environ", {"OURA_OWNERS": ""}):
        assert get_role("stranger", "alice") is Role.OWNER


def test_owners_whitespace_trimmed():
    with patch.dict("os.environ", {"OURA_OWNERS": " alice , bob "}):
        assert get_role("alice", "charlie") is Role.OWNER


# ---------------------------------------------------------------------------
# filter_records
# ---------------------------------------------------------------------------

_FULL_SLEEP = [
    {
        "day": "2024-01-01",
        "score": 85,
        "total_sleep_duration": 28800,
        "rem_sleep_duration": 7200,
        "average_hrv": 52,
        "average_heart_rate": 58,
    }
]

_FULL_READINESS = [
    {
        "day": "2024-01-01",
        "score": 72,
        "temperature_deviation": -0.1,
        "hrv_balance_score": 80,
        "resting_heart_rate_score": 90,
    }
]


def test_owner_sees_all_fields():
    result = filter_records(_FULL_SLEEP, Role.OWNER)
    assert result == _FULL_SLEEP


def test_friend_sees_only_score_fields():
    result = filter_records(_FULL_SLEEP, Role.FRIEND)
    assert result == [{"day": "2024-01-01", "score": 85}]


def test_friend_sees_only_score_fields_readiness():
    result = filter_records(_FULL_READINESS, Role.FRIEND)
    assert result == [{"day": "2024-01-01", "score": 72}]


def test_filter_empty_records():
    assert filter_records([], Role.FRIEND) == []
    assert filter_records([], Role.OWNER) == []


def test_friend_multiple_records():
    records = [
        {"day": "2024-01-01", "score": 85, "total_sleep_duration": 28800},
        {"day": "2024-01-02", "score": 78, "total_sleep_duration": 25200},
    ]
    result = filter_records(records, Role.FRIEND)
    assert result == [
        {"day": "2024-01-01", "score": 85},
        {"day": "2024-01-02", "score": 78},
    ]


# ---------------------------------------------------------------------------
# API integration — access scoping via viewer_id query param
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    from oura_fun.api.app import app
    from fastapi.testclient import TestClient
    return TestClient(app)


def test_no_viewer_id_returns_full_records(client):
    """Default (no viewer_id) → owner role → full records returned."""
    fake = [{"day": "2024-01-01", "score": 85, "total_sleep_duration": 28800}]
    with patch("oura_fun.api.app.db.get_sleep", return_value=fake):
        r = client.get("/api/sleep/alice")
    assert r.status_code == 200
    body = r.json()
    assert body["viewer_role"] == "owner"
    assert body["records"] == fake


def test_friend_viewer_gets_score_only(client):
    fake = [{"day": "2024-01-01", "score": 85, "total_sleep_duration": 28800}]
    with (
        patch("oura_fun.api.app.db.get_sleep", return_value=fake),
        patch.dict("os.environ", {"OURA_OWNERS": "alice"}),
    ):
        r = client.get("/api/sleep/alice?viewer_id=charlie")
    assert r.status_code == 200
    body = r.json()
    assert body["viewer_role"] == "friend"
    assert body["records"] == [{"day": "2024-01-01", "score": 85}]


def test_owner_viewer_gets_full_records(client):
    fake = [{"day": "2024-01-01", "score": 85, "total_sleep_duration": 28800}]
    with (
        patch("oura_fun.api.app.db.get_sleep", return_value=fake),
        patch.dict("os.environ", {"OURA_OWNERS": "alice,bob"}),
    ):
        r = client.get("/api/sleep/alice?viewer_id=bob")
    assert r.status_code == 200
    body = r.json()
    assert body["viewer_role"] == "owner"
    assert body["records"] == fake


def test_self_viewer_gets_full_records(client):
    """viewer_id == person_id → always owner access."""
    fake = [{"day": "2024-01-01", "score": 85, "average_hrv": 55}]
    with (
        patch("oura_fun.api.app.db.get_sleep", return_value=fake),
        patch.dict("os.environ", {"OURA_OWNERS": ""}),
    ):
        r = client.get("/api/sleep/alice?viewer_id=alice")
    assert r.status_code == 200
    body = r.json()
    assert body["viewer_role"] == "owner"
    assert body["records"] == fake


def test_readiness_friend_scoped(client):
    fake = [{"day": "2024-01-01", "score": 72, "temperature_deviation": -0.1}]
    with (
        patch("oura_fun.api.app.db.get_readiness", return_value=fake),
        patch.dict("os.environ", {"OURA_OWNERS": "alice"}),
    ):
        r = client.get("/api/readiness/alice?viewer_id=charlie")
    assert r.status_code == 200
    assert r.json()["records"] == [{"day": "2024-01-01", "score": 72}]


def test_activity_friend_scoped(client):
    fake = [{"day": "2024-01-01", "score": 90, "steps": 12000}]
    with (
        patch("oura_fun.api.app.db.get_activity", return_value=fake),
        patch.dict("os.environ", {"OURA_OWNERS": "alice"}),
    ):
        r = client.get("/api/activity/alice?viewer_id=charlie")
    assert r.status_code == 200
    assert r.json()["records"] == [{"day": "2024-01-01", "score": 90}]


def test_compare_friend_scoped(client):
    fake = [{"day": "2024-01-01", "score": 80, "hrv_balance_score": 85}]
    with (
        patch("oura_fun.api.app.db.list_people", return_value=["alice"]),
        patch("oura_fun.api.app.db.get_readiness", return_value=fake),
        patch.dict("os.environ", {"OURA_OWNERS": "alice"}),
    ):
        r = client.get("/api/compare?metric=readiness&viewer_id=charlie")
    assert r.status_code == 200
    assert r.json()["people"]["alice"] == [{"day": "2024-01-01", "score": 80}]
