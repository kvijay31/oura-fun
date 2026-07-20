"""Tests for F3.1: MCP server scaffold + core query tools.
Also covers F3.3: run_sql read-only escape hatch.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

import oura_fun.mcp_server as _mod
from oura_fun.mcp_server import mcp, query_activity, query_readiness, query_sleep, run_sql

_SLEEP_ROW = {
    "day": "2025-01-15",
    "score": 82,
    "total_sleep_duration": 27000,
    "rem_sleep_duration": 5400,
    "deep_sleep_duration": 3600,
    "light_sleep_duration": 18000,
    "efficiency": 95,
    "restless_periods": 3,
    "average_hrv": 48.5,
    "average_heart_rate": 55.0,
}

_READINESS_ROW = {
    "day": "2025-01-15",
    "score": 78,
    "temperature_deviation": -0.1,
    "temperature_trend_deviation": 0.0,
    "hrv_balance_score": 75,
    "recovery_index_score": 80,
    "resting_heart_rate_score": 82,
    "sleep_balance_score": 77,
    "previous_night_score": 82,
    "previous_day_score": 70,
    "activity_balance_score": 65,
}

_ACTIVITY_ROW = {
    "day": "2025-01-15",
    "score": 90,
    "active_calories": 450,
    "total_calories": 2200,
    "target_calories": 500,
    "steps": 9500,
    "equivalent_walking_minutes": 75,
    "high_activity_time": 1800,
    "medium_activity_time": 3600,
    "low_activity_time": 7200,
    "sedentary_time": 28800,
    "resting_time": 28800,
    "meet_daily_targets": 1,
    "move_every_hour": 1,
    "recovery_time": 0,
    "stay_active": 1,
    "training_frequency": 1,
    "training_volume": 1,
}


def test_mcp_server_has_three_tools():
    tool_names = {t.name for t in mcp._tool_manager.list_tools()}
    assert {"query_sleep", "query_readiness", "query_activity"} <= tool_names


def test_query_sleep_returns_rows():
    with patch("oura_fun.mcp_server.get_sleep", return_value=[_SLEEP_ROW]):
        result = query_sleep("kartik", "2025-01-15", "2025-01-15")
    rows = json.loads(result)
    assert isinstance(rows, list)
    assert rows[0]["score"] == 82
    assert rows[0]["day"] == "2025-01-15"


def test_query_sleep_empty():
    with patch("oura_fun.mcp_server.get_sleep", return_value=[]):
        result = query_sleep("kartik", "2025-01-15", "2025-01-15")
    data = json.loads(result)
    assert data["records"] == []
    assert data["person"] == "kartik"


def test_query_readiness_returns_rows():
    with patch("oura_fun.mcp_server.get_readiness", return_value=[_READINESS_ROW]):
        result = query_readiness("kartik", "2025-01-15", "2025-01-15")
    rows = json.loads(result)
    assert rows[0]["score"] == 78
    assert "temperature_deviation" in rows[0]


def test_query_readiness_empty():
    with patch("oura_fun.mcp_server.get_readiness", return_value=[]):
        result = query_readiness("partner", "2025-01-01", "2025-01-01")
    data = json.loads(result)
    assert data["records"] == []
    assert data["person"] == "partner"


def test_query_activity_returns_rows():
    with patch("oura_fun.mcp_server.get_activity", return_value=[_ACTIVITY_ROW]):
        result = query_activity("kartik", "2025-01-15", "2025-01-15")
    rows = json.loads(result)
    assert rows[0]["steps"] == 9500
    assert rows[0]["score"] == 90


def test_query_activity_empty():
    with patch("oura_fun.mcp_server.get_activity", return_value=[]):
        result = query_activity("kartik", "2025-01-15", "2025-01-15")
    data = json.loads(result)
    assert data["records"] == []


def test_query_sleep_passes_args_to_db():
    with patch("oura_fun.mcp_server.get_sleep", return_value=[]) as mock_fn:
        query_sleep("partner", "2025-03-01", "2025-03-31")
    mock_fn.assert_called_once_with("partner", "2025-03-01", "2025-03-31")


def test_query_readiness_passes_args_to_db():
    with patch("oura_fun.mcp_server.get_readiness", return_value=[]) as mock_fn:
        query_readiness("kartik", "2025-03-01", "2025-03-07")
    mock_fn.assert_called_once_with("kartik", "2025-03-01", "2025-03-07")


def test_query_activity_passes_args_to_db():
    with patch("oura_fun.mcp_server.get_activity", return_value=[]) as mock_fn:
        query_activity("kartik", "2025-03-01", "2025-03-07")
    mock_fn.assert_called_once_with("kartik", "2025-03-01", "2025-03-07")


def test_main_callable():
    assert callable(_mod.main)


# --- F3.3: run_sql ---

_SQL_ROWS = [{"day": "2025-01-15", "score": 82}]


def test_run_sql_select_returns_rows():
    with patch("oura_fun.mcp_server._run_sql", return_value=_SQL_ROWS):
        result = run_sql("SELECT * FROM v_sleep_nightly")
    rows = json.loads(result)
    assert rows[0]["score"] == 82


def test_run_sql_with_cte_allowed():
    with patch("oura_fun.mcp_server._run_sql", return_value=_SQL_ROWS):
        result = run_sql("WITH cte AS (SELECT 1) SELECT * FROM cte")
    rows = json.loads(result)
    assert rows[0]["score"] == 82


def test_run_sql_rejects_insert():
    with patch("oura_fun.mcp_server._run_sql") as mock_fn:
        result = run_sql("INSERT INTO v_sleep_nightly VALUES (1)")
    mock_fn.assert_not_called()
    assert "Error" in result
    assert "SELECT" in result


def test_run_sql_rejects_drop():
    with patch("oura_fun.mcp_server._run_sql") as mock_fn:
        result = run_sql("DROP TABLE v_sleep_nightly")
    mock_fn.assert_not_called()
    assert "Error" in result


def test_run_sql_rejects_update():
    with patch("oura_fun.mcp_server._run_sql") as mock_fn:
        result = run_sql("UPDATE v_sleep_nightly SET score = 0")
    mock_fn.assert_not_called()
    assert "Error" in result


def test_run_sql_case_insensitive():
    with patch("oura_fun.mcp_server._run_sql", return_value=_SQL_ROWS):
        result = run_sql("select * from v_sleep_nightly")
    rows = json.loads(result)
    assert rows[0]["score"] == 82


def test_run_sql_leading_whitespace():
    with patch("oura_fun.mcp_server._run_sql", return_value=_SQL_ROWS):
        result = run_sql("  \n  SELECT * FROM v_sleep_nightly")
    rows = json.loads(result)
    assert rows[0]["score"] == 82


def test_run_sql_empty_result():
    with patch("oura_fun.mcp_server._run_sql", return_value=[]):
        result = run_sql("SELECT * FROM v_sleep_nightly WHERE 1=0")
    rows = json.loads(result)
    assert rows == []


def test_run_sql_tool_registered():
    tool_names = {t.name for t in mcp._tool_manager.list_tools()}
    assert "run_sql" in tool_names
