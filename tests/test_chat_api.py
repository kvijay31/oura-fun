"""Tests for the chat API route — logic only, no external I/O."""

import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# _execute_mcp_tool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_mcp_tool_no_cmd_configured():
    from oura_fun.api.routes.chat import _execute_mcp_tool

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OURA_MCP_CMD", None)
        result = await _execute_mcp_tool("query_sleep", {"person": "kartik", "start": "2024-01-01", "end": "2024-01-07"})

    assert "OURA_MCP_CMD" in result or "not configured" in result.lower()


@pytest.mark.asyncio
async def test_execute_mcp_tool_mcp_not_installed():
    from oura_fun.api.routes.chat import _execute_mcp_tool

    with patch.dict(os.environ, {"OURA_MCP_CMD": "uv run python -m oura_fun.mcp_server"}):
        # Simulate mcp package not installed
        with patch.dict("sys.modules", {"mcp": None, "mcp.client.stdio": None}):
            result = await _execute_mcp_tool("query_sleep", {})

    # Should get an import-error message, not an exception
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------


def test_oura_tools_schema_valid():
    from oura_fun.api.routes.chat import OURA_TOOLS

    expected_names = {
        "query_sleep",
        "query_readiness",
        "query_activity",
        "compare_people",
        "baseline",
        "run_sql",
    }
    actual_names = {t["name"] for t in OURA_TOOLS}
    assert actual_names == expected_names


def test_each_tool_has_required_fields():
    from oura_fun.api.routes.chat import OURA_TOOLS

    for tool in OURA_TOOLS:
        assert "name" in tool
        assert "description" in tool
        assert "input_schema" in tool
        schema = tool["input_schema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema


def test_query_tools_require_person_start_end():
    from oura_fun.api.routes.chat import OURA_TOOLS

    for name in ("query_sleep", "query_readiness", "query_activity"):
        tool = next(t for t in OURA_TOOLS if t["name"] == name)
        required = set(tool["input_schema"]["required"])
        assert {"person", "start", "end"} <= required, f"{name} missing required fields"


def test_run_sql_requires_query():
    from oura_fun.api.routes.chat import OURA_TOOLS

    tool = next(t for t in OURA_TOOLS if t["name"] == "run_sql")
    assert "query" in tool["input_schema"]["required"]


# ---------------------------------------------------------------------------
# FastAPI app smoke test
# ---------------------------------------------------------------------------


def test_health_endpoint():
    from fastapi.testclient import TestClient
    from oura_fun.api.main import app

    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_endpoint_returns_sse_without_api_key(monkeypatch):
    """Without ANTHROPIC_API_KEY the endpoint should stream an error event."""
    from fastapi.testclient import TestClient
    from oura_fun.api.main import app

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    client = TestClient(app)
    resp = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    body = resp.text
    # Should contain an error event
    events = [
        json.loads(line[6:])
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    assert any(e.get("type") == "error" for e in events)
