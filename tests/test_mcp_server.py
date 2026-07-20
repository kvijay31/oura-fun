"""Tests for the oura-fun MCP server: query tools and data-dictionary resource."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

import oura_fun.mcp_server as _mod
from oura_fun.mcp_server import _DATA_DICTIONARY, data_dictionary, mcp, query_activity, query_readiness, query_sleep

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


# ── F3.4: Data dictionary resource ───────────────────────────────────────────

def test_data_dictionary_resource_registered():
    resource_uris = set(mcp._resource_manager._resources.keys())
    assert "oura://data-dictionary" in resource_uris


def test_data_dictionary_returns_valid_json():
    result = data_dictionary()
    parsed = json.loads(result)
    assert isinstance(parsed, dict)


def test_data_dictionary_has_top_level_keys():
    parsed = json.loads(data_dictionary())
    assert "description" in parsed
    assert "common_fields" in parsed
    assert "views" in parsed


def test_data_dictionary_covers_all_views():
    expected_views = {
        "v_sleep_nightly",
        "v_readiness_daily",
        "v_activity_daily",
        "v_stress_daily",
        "v_spo2_daily",
        "v_sleep_period",
        "v_sleep_time",
        "v_heartrate",
        "v_workout",
        "v_session",
        "v_enhanced_tag",
        "v_personal_info",
    }
    parsed = json.loads(data_dictionary())
    assert expected_views == set(parsed["views"].keys())


def test_data_dictionary_contributor_fields_described():
    parsed = json.loads(data_dictionary())
    sleep_fields = parsed["views"]["v_sleep_nightly"]["fields"]
    # All seven sleep contributor sub-scores must be present and documented
    for name in ("c_deep_sleep", "c_efficiency", "c_latency", "c_rem_sleep",
                 "c_restfulness", "c_timing", "c_total_sleep"):
        assert name in sleep_fields, f"Missing contributor field: {name}"
        assert sleep_fields[name]["description"], f"Empty description for {name}"


def test_data_dictionary_c_timing_explains_circadian():
    """c_timing is the most commonly misunderstood contributor — verify it has a useful description."""
    parsed = json.loads(data_dictionary())
    desc = parsed["views"]["v_sleep_nightly"]["fields"]["c_timing"]["description"]
    assert "circadian" in desc.lower() or "clock" in desc.lower()


def test_data_dictionary_readiness_contributors_complete():
    parsed = json.loads(data_dictionary())
    fields = parsed["views"]["v_readiness_daily"]["fields"]
    for name in ("c_hrv_balance", "c_resting_heart_rate", "c_sleep_balance",
                 "c_recovery_index", "c_activity_balance", "c_body_temperature",
                 "c_previous_night", "c_previous_day_activity"):
        assert name in fields, f"Missing readiness contributor: {name}"


def test_data_dictionary_activity_contributors_complete():
    parsed = json.loads(data_dictionary())
    fields = parsed["views"]["v_activity_daily"]["fields"]
    for name in ("c_meet_daily_targets", "c_move_every_hour", "c_recovery_time",
                 "c_stay_active", "c_training_frequency", "c_training_volume"):
        assert name in fields, f"Missing activity contributor: {name}"


def test_data_dictionary_common_fields_present():
    parsed = json.loads(data_dictionary())
    for key in ("person_id", "natural_key", "day", "fetched_at"):
        assert key in parsed["common_fields"], f"Missing common field: {key}"


def test_data_dictionary_dict_matches_function_output():
    assert json.loads(data_dictionary()) == _DATA_DICTIONARY
