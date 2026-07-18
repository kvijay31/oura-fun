"""Tests for the chat API endpoint and tool execution."""

import json
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from oura_fun.api.app import app
    return TestClient(app)


def _collect_sse(response) -> list[dict]:
    events = []
    for line in response.text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


def test_chat_missing_api_key(client):
    with patch.dict("os.environ", {}, clear=True):
        import os
        os.environ.pop("ANTHROPIC_API_KEY", None)
        r = client.post("/api/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 200
    events = _collect_sse(r)
    assert any(e.get("type") == "error" for e in events)
    err = next(e for e in events if e.get("type") == "error")
    assert "ANTHROPIC_API_KEY" in err["message"]


def test_chat_returns_sse_content_type(client):
    with patch.dict("os.environ", {}, clear=True):
        import os
        os.environ.pop("ANTHROPIC_API_KEY", None)
        r = client.post("/api/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert "text/event-stream" in r.headers["content-type"]


# ── Tool execution unit tests ──────────────────────────────────────────────

def test_execute_tool_query_sleep():
    from oura_fun.api.chat import execute_tool
    fake = [{"day": "2024-01-01", "score": 85}]
    with patch("oura_fun.api.chat.db.get_sleep", return_value=fake):
        result = execute_tool("query_sleep", {"person": "alice", "start": "2024-01-01", "end": "2024-01-31"})
    assert json.loads(result) == fake


def test_execute_tool_query_readiness():
    from oura_fun.api.chat import execute_tool
    fake = [{"day": "2024-01-01", "score": 72}]
    with patch("oura_fun.api.chat.db.get_readiness", return_value=fake):
        result = execute_tool("query_readiness", {"person": "alice", "start": "2024-01-01", "end": "2024-01-31"})
    assert json.loads(result) == fake


def test_execute_tool_query_activity():
    from oura_fun.api.chat import execute_tool
    fake = [{"day": "2024-01-01", "score": 90}]
    with patch("oura_fun.api.chat.db.get_activity", return_value=fake):
        result = execute_tool("query_activity", {"person": "alice", "start": "2024-01-01", "end": "2024-01-31"})
    assert json.loads(result) == fake


def test_execute_tool_compare_people():
    from oura_fun.api.chat import execute_tool
    fake = [{"day": "2024-01-01", "score": 80}]
    with (
        patch("oura_fun.api.chat.db.list_people", return_value=["alice", "bob"]),
        patch("oura_fun.api.chat.db.get_sleep", return_value=fake),
    ):
        result = execute_tool("compare_people", {"metric": "sleep", "start": "2024-01-01", "end": "2024-01-31"})
    data = json.loads(result)
    assert "alice" in data
    assert "bob" in data


def test_execute_tool_compare_unknown_metric():
    from oura_fun.api.chat import execute_tool
    result = execute_tool("compare_people", {"metric": "stress", "start": "2024-01-01", "end": "2024-01-31"})
    assert "error" in json.loads(result)


def test_execute_tool_baseline():
    from oura_fun.api.chat import execute_tool
    fake = [{"day": f"2024-01-{i:02d}", "score": 70 + i} for i in range(1, 11)]
    with patch("oura_fun.api.chat.db.get_sleep", return_value=fake):
        result = execute_tool("baseline", {"person": "alice", "metric": "sleep", "window": 90})
    data = json.loads(result)
    assert data["n"] == 10
    assert data["mean"] is not None
    assert data["stdev"] is not None


def test_execute_tool_baseline_no_data():
    from oura_fun.api.chat import execute_tool
    with patch("oura_fun.api.chat.db.get_sleep", return_value=[]):
        result = execute_tool("baseline", {"person": "alice", "metric": "sleep"})
    data = json.loads(result)
    assert data["n"] == 0
    assert data["mean"] is None


def test_execute_tool_run_sql_select():
    from oura_fun.api.chat import execute_tool
    fake = [{"score": 85}]
    with patch("oura_fun.api.chat.db._query", return_value=fake):
        result = execute_tool("run_sql", {"query": "SELECT score FROM v_sleep_nightly LIMIT 1"})
    assert json.loads(result) == fake


def test_execute_tool_run_sql_rejects_non_select():
    from oura_fun.api.chat import execute_tool
    result = execute_tool("run_sql", {"query": "DROP TABLE v_sleep_nightly"})
    assert "error" in json.loads(result)
    assert "SELECT" in json.loads(result)["error"]


def test_execute_tool_unknown():
    from oura_fun.api.chat import execute_tool
    result = execute_tool("nonexistent_tool", {})
    assert "error" in json.loads(result)
