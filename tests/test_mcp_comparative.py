"""Tests for F3.2: compare_people and baseline MCP tools."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from oura_fun.api.db import METRIC_CATALOG
from oura_fun.mcp_server import baseline, compare_people, mcp


def test_mcp_server_has_compare_and_baseline_tools():
    tool_names = {t.name for t in mcp._tool_manager.list_tools()}
    assert {"compare_people", "baseline"} <= tool_names


# ── compare_people ──────────────────────────────────────────────────────────

_COMPARE_ROWS = [
    {"person_id": "kartik", "day": "2025-01-15", "value": 82},
    {"person_id": "partner", "day": "2025-01-15", "value": 75},
]


def test_compare_people_returns_rows():
    with patch("oura_fun.mcp_server.compare_people_metric", return_value=_COMPARE_ROWS):
        result = compare_people("sleep_score", "kartik,partner", "2025-01-15", "2025-01-15")
    rows = json.loads(result)
    assert isinstance(rows, list)
    assert len(rows) == 2
    assert rows[0]["person_id"] == "kartik"
    assert rows[0]["value"] == 82
    assert rows[1]["person_id"] == "partner"


def test_compare_people_empty_result():
    with patch("oura_fun.mcp_server.compare_people_metric", return_value=[]):
        result = compare_people("sleep_score", "kartik,partner", "2025-01-15", "2025-01-15")
    data = json.loads(result)
    assert data["records"] == []
    assert data["metric"] == "sleep_score"
    assert "kartik" in data["people"]


def test_compare_people_unknown_metric():
    result = compare_people("nonexistent_metric", "kartik", "2025-01-01", "2025-01-31")
    data = json.loads(result)
    assert "error" in data
    assert "supported_metrics" in data
    assert "sleep_score" in data["supported_metrics"]


def test_compare_people_no_people():
    result = compare_people("sleep_score", "  ,  ", "2025-01-01", "2025-01-31")
    data = json.loads(result)
    assert "error" in data


def test_compare_people_passes_correct_args():
    with patch("oura_fun.mcp_server.compare_people_metric", return_value=[]) as mock_fn:
        compare_people("steps", "kartik,partner", "2025-03-01", "2025-03-31")
    mock_fn.assert_called_once_with("steps", ["kartik", "partner"], "2025-03-01", "2025-03-31")


def test_compare_people_strips_whitespace_in_people():
    with patch("oura_fun.mcp_server.compare_people_metric", return_value=[]) as mock_fn:
        compare_people("steps", " kartik , partner ", "2025-01-01", "2025-01-31")
    call_args = mock_fn.call_args[0]
    assert call_args[1] == ["kartik", "partner"]


# ── baseline ────────────────────────────────────────────────────────────────

_BASELINE_RESULT = {
    "person": "kartik",
    "metric": "sleep_score",
    "window_days": 90,
    "start": "2024-10-18",
    "end": "2025-01-15",
    "mean": 78.5,
    "stdev": 6.2,
    "count": 85,
}


def test_baseline_returns_stats():
    with patch("oura_fun.mcp_server.get_baseline", return_value=_BASELINE_RESULT):
        result = baseline("kartik", "sleep_score", 90)
    data = json.loads(result)
    assert data["mean"] == 78.5
    assert data["stdev"] == 6.2
    assert data["count"] == 85
    assert data["person"] == "kartik"
    assert data["metric"] == "sleep_score"


def test_baseline_no_data():
    with patch("oura_fun.mcp_server.get_baseline", return_value=None):
        result = baseline("kartik", "sleep_score", 90)
    data = json.loads(result)
    assert data["mean"] is None
    assert data["stdev"] is None
    assert data["count"] == 0


def test_baseline_unknown_metric():
    result = baseline("kartik", "nonexistent_metric", 90)
    data = json.loads(result)
    assert "error" in data
    assert "supported_metrics" in data


def test_baseline_invalid_window():
    result = baseline("kartik", "sleep_score", 0)
    data = json.loads(result)
    assert "error" in data


def test_baseline_passes_correct_args():
    with patch("oura_fun.mcp_server.get_baseline", return_value=None) as mock_fn:
        baseline("partner", "readiness_score", 30)
    mock_fn.assert_called_once_with("partner", "readiness_score", 30)


# ── METRIC_CATALOG ───────────────────────────────────────────────────────────

def test_metric_catalog_nonempty():
    assert len(METRIC_CATALOG) > 0


def test_metric_catalog_all_entries_have_three_fields():
    for name, entry in METRIC_CATALOG.items():
        assert len(entry) == 3, f"{name}: expected (view, column, filter), got {entry}"
        view, column, extra = entry
        assert isinstance(view, str) and view
        assert isinstance(column, str) and column
        assert extra is None or isinstance(extra, str)


def test_compare_people_metric_in_catalog():
    assert "sleep_score" in METRIC_CATALOG
    assert "readiness_score" in METRIC_CATALOG
    assert "activity_score" in METRIC_CATALOG
    assert "steps" in METRIC_CATALOG
    assert "average_hrv" in METRIC_CATALOG
