"""Tests for F10.1 on-demand refresh endpoint and throttle logic."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_refresh_state():
    """Reset module-level refresh state between tests."""
    from oura_fun.api import refresh as r
    with r._state_lock:
        r._state.clear()
    yield
    with r._state_lock:
        r._state.clear()


@pytest.fixture
def client():
    from oura_fun.api.app import app
    return TestClient(app)


# --- throttle logic ---

def test_no_tokens_returns_empty():
    from oura_fun.api.refresh import start_refresh
    with patch("oura_fun.api.refresh.settings") as mock_settings:
        mock_settings.tokens.return_value = {}
        result = start_refresh()
    assert result == {}


def test_unknown_person_returns_no_token():
    from oura_fun.api.refresh import start_refresh
    with patch("oura_fun.api.refresh.settings") as mock_settings:
        mock_settings.tokens.return_value = {"alice": "tok"}
        result = start_refresh("bob")
    assert result == {"bob": "no_token"}


def test_first_refresh_starts():
    from oura_fun.api.refresh import start_refresh
    with (
        patch("oura_fun.api.refresh.settings") as mock_settings,
        patch("oura_fun.api.refresh._executor") as mock_exec,
    ):
        mock_settings.tokens.return_value = {"alice": "tok"}
        mock_exec.submit = MagicMock()
        result = start_refresh("alice")
    assert result == {"alice": "started"}
    mock_exec.submit.assert_called_once()


def test_throttle_within_window():
    from oura_fun.api import refresh as r
    with r._state_lock:
        r._state["alice"] = {
            "running": False,
            "last_refresh": datetime.now(timezone.utc) - timedelta(seconds=60),
            "error": None,
        }
    with (
        patch("oura_fun.api.refresh.settings") as mock_settings,
        patch("oura_fun.api.refresh._executor") as mock_exec,
    ):
        mock_settings.tokens.return_value = {"alice": "tok"}
        mock_exec.submit = MagicMock()
        result = r.start_refresh("alice")
    assert "throttled" in result["alice"]
    mock_exec.submit.assert_not_called()


def test_throttle_expired_allows_refresh():
    from oura_fun.api import refresh as r
    with r._state_lock:
        r._state["alice"] = {
            "running": False,
            "last_refresh": datetime.now(timezone.utc) - timedelta(seconds=400),
            "error": None,
        }
    with (
        patch("oura_fun.api.refresh.settings") as mock_settings,
        patch("oura_fun.api.refresh._executor") as mock_exec,
    ):
        mock_settings.tokens.return_value = {"alice": "tok"}
        mock_exec.submit = MagicMock()
        result = r.start_refresh("alice")
    assert result["alice"] == "started"
    mock_exec.submit.assert_called_once()


def test_already_running_throttled():
    from oura_fun.api import refresh as r
    with r._state_lock:
        r._state["alice"] = {"running": True, "last_refresh": None, "error": None}
    with (
        patch("oura_fun.api.refresh.settings") as mock_settings,
        patch("oura_fun.api.refresh._executor") as mock_exec,
    ):
        mock_settings.tokens.return_value = {"alice": "tok"}
        mock_exec.submit = MagicMock()
        result = r.start_refresh("alice")
    assert result["alice"] == "already_running"
    mock_exec.submit.assert_not_called()


# --- get_status ---

def test_get_status_empty():
    from oura_fun.api.refresh import get_status
    assert get_status() == {}


def test_get_status_with_state():
    from oura_fun.api import refresh as r
    ts = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    with r._state_lock:
        r._state["alice"] = {"running": False, "last_refresh": ts, "error": None}
    status = r.get_status()
    assert status["alice"]["running"] is False
    assert status["alice"]["last_refresh"] == ts.isoformat()
    assert status["alice"]["error"] is None


def test_any_running_true():
    from oura_fun.api import refresh as r
    with r._state_lock:
        r._state["alice"] = {"running": True, "last_refresh": None, "error": None}
    assert r.any_running() is True


def test_any_running_false():
    from oura_fun.api import refresh as r
    with r._state_lock:
        r._state["alice"] = {"running": False, "last_refresh": None, "error": None}
    assert r.any_running() is False


# --- API endpoints ---

def test_refresh_all_endpoint(client):
    with (
        patch("oura_fun.api.refresh.settings") as mock_settings,
        patch("oura_fun.api.refresh._executor") as mock_exec,
    ):
        mock_settings.tokens.return_value = {"alice": "tok"}
        mock_exec.submit = MagicMock()
        r = client.post("/api/refresh")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"]["alice"] == "started"


def test_refresh_person_endpoint(client):
    with (
        patch("oura_fun.api.refresh.settings") as mock_settings,
        patch("oura_fun.api.refresh._executor") as mock_exec,
    ):
        mock_settings.tokens.return_value = {"alice": "tok", "bob": "tok2"}
        mock_exec.submit = MagicMock()
        r = client.post("/api/refresh/alice")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == {"alice": "started"}


def test_refresh_status_endpoint(client):
    r = client.get("/api/refresh/status")
    assert r.status_code == 200
    data = r.json()
    assert "refresh" in data
    assert "any_running" in data
    assert data["any_running"] is False


# --- DBLockedError handling ---

def test_db_locked_returns_503(client):
    from oura_fun.api.db import DBLockedError
    with patch("oura_fun.api.app.db.get_sleep", side_effect=DBLockedError("locked")):
        r = client.get("/api/sleep/alice")
    assert r.status_code == 503
    data = r.json()
    assert data["error"] == "db_locked"
    assert "refresh_running" in data


def test_db_locked_error_detection():
    """DBLockedError is raised when the DB error message contains lock keywords."""
    import duckdb
    from oura_fun.api.db import _conn, DBLockedError
    with patch("duckdb.connect", side_effect=Exception("database is locked: held by another process")):
        with pytest.raises(DBLockedError):
            with _conn() as _:
                pass


def test_db_unavailable_yields_none():
    """Non-lock DB errors still yield None (empty results, not an exception)."""
    from oura_fun.api.db import _conn
    with patch("duckdb.connect", side_effect=Exception("file not found")):
        with _conn() as con:
            assert con is None
