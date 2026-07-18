import json
import os
from typing import AsyncIterator

import anthropic
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()

OURA_TOOLS: list[dict] = [
    {
        "name": "query_sleep",
        "description": (
            "Query nightly sleep data for a person within a date range. "
            "Returns sleep score, total duration, sleep stages (deep, REM, light), "
            "HRV average, resting heart rate, efficiency, and latency."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "person": {
                    "type": "string",
                    "description": "Person identifier as configured (e.g. 'kartik', 'partner')",
                },
                "start": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format (inclusive)",
                },
                "end": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format (inclusive)",
                },
            },
            "required": ["person", "start", "end"],
        },
    },
    {
        "name": "query_readiness",
        "description": (
            "Query daily readiness data for a person within a date range. "
            "Returns readiness score and contributor breakdown "
            "(HRV balance, resting HR, recovery index, sleep balance, activity balance, body temperature)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "person": {"type": "string"},
                "start": {"type": "string", "description": "YYYY-MM-DD"},
                "end": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["person", "start", "end"],
        },
    },
    {
        "name": "query_activity",
        "description": (
            "Query daily activity data for a person within a date range. "
            "Returns activity score, steps, active calories, total calories, "
            "equivalent walking distance, and inactivity alerts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "person": {"type": "string"},
                "start": {"type": "string", "description": "YYYY-MM-DD"},
                "end": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["person", "start", "end"],
        },
    },
    {
        "name": "compare_people",
        "description": (
            "Compare a metric across multiple people over a date range. "
            "Useful for household comparisons."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "description": (
                        "Metric to compare, e.g. 'sleep_score', 'readiness_score', "
                        "'activity_score', 'hrv_average', 'resting_heart_rate'"
                    ),
                },
                "people": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of person identifiers",
                },
                "start": {"type": "string", "description": "YYYY-MM-DD"},
                "end": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["metric", "people", "start", "end"],
        },
    },
    {
        "name": "baseline",
        "description": (
            "Compute baseline statistics (mean and standard deviation) for a "
            "person's metric over a rolling window. Useful for z-scoring."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "person": {"type": "string"},
                "metric": {
                    "type": "string",
                    "description": "Metric name, e.g. 'sleep_score', 'hrv_average', 'resting_heart_rate'",
                },
                "window": {
                    "type": "integer",
                    "description": "Number of past days to compute baseline over (e.g. 90)",
                },
            },
            "required": ["person", "metric", "window"],
        },
    },
    {
        "name": "run_sql",
        "description": (
            "Run a read-only SQL SELECT query directly against the Oura DuckDB views. "
            "Available views: v_sleep_nightly, v_readiness_daily, v_activity_daily. "
            "Only SELECT statements are permitted."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SQL SELECT query to execute against the views",
                },
            },
            "required": ["query"],
        },
    },
]

SYSTEM_PROMPT = """You are an AI health assistant with access to Oura Ring data via structured tools. You can query sleep, readiness, and activity data.

When a user asks about their health data:
- Use the appropriate tool(s) to fetch real data before answering
- Reference specific numbers and dates, not generic advice
- Explain what the numbers mean (e.g., an HRV of 45ms is good/low/high relative to baseline)
- Note meaningful trends, not just isolated values
- If a tool returns an error about the MCP server not being configured, explain that the Oura data backend needs to be set up (Phase 3 of the project) and suggest the user configure OURA_MCP_CMD

Today's date context: use the current date when "today", "this week", "last month" etc. are mentioned."""


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


async def _execute_mcp_tool(tool_name: str, tool_input: dict) -> str:
    mcp_cmd = os.environ.get("OURA_MCP_CMD", "").strip()
    if not mcp_cmd:
        return (
            "Oura data backend not configured. "
            "Set the OURA_MCP_CMD environment variable to the command that starts the MCP server, "
            "for example: OURA_MCP_CMD='uv run python -m oura_fun.mcp_server'. "
            "The MCP server is built in Phase 3 (F3.1-F3.3) of this project."
        )

    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        parts = mcp_cmd.split()
        server_params = StdioServerParameters(command=parts[0], args=parts[1:])

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=tool_input)
                if result.content:
                    parts_text = [
                        c.text for c in result.content if hasattr(c, "text") and c.text
                    ]
                    return "\n".join(parts_text) if parts_text else "Tool returned no data"
                return "Tool returned no data"
    except ImportError:
        return "MCP Python SDK not installed. Run: uv add mcp"
    except Exception as e:
        return f"MCP tool execution failed: {e}"


async def _stream_chat(messages: list[ChatMessage]) -> AsyncIterator[str]:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        yield f"data: {json.dumps({'type': 'error', 'message': 'ANTHROPIC_API_KEY not configured in .env'})}\n\n"
        return

    client = anthropic.AsyncAnthropic(api_key=api_key)
    conversation: list[dict] = [{"role": m.role, "content": m.content} for m in messages]

    while True:
        response_text = ""
        tool_calls: list[dict] = []
        current_tool: dict | None = None

        async with client.messages.stream(
            model="claude-sonnet-5",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=conversation,
            tools=OURA_TOOLS,  # type: ignore[arg-type]
        ) as stream:
            async for event in stream:
                etype = getattr(event, "type", None)

                if etype == "content_block_start":
                    block = getattr(event, "content_block", None)
                    if block and getattr(block, "type", None) == "tool_use":
                        current_tool = {
                            "id": block.id,
                            "name": block.name,
                            "input_raw": "",
                        }
                        yield f"data: {json.dumps({'type': 'tool_start', 'name': block.name})}\n\n"

                elif etype == "content_block_delta":
                    delta = getattr(event, "delta", None)
                    if delta:
                        dtype = getattr(delta, "type", None)
                        if dtype == "text_delta":
                            chunk = delta.text
                            response_text += chunk
                            yield f"data: {json.dumps({'type': 'text', 'text': chunk})}\n\n"
                        elif dtype == "input_json_delta" and current_tool is not None:
                            current_tool["input_raw"] += delta.partial_json

                elif etype == "content_block_stop":
                    if current_tool is not None:
                        try:
                            current_tool["input"] = (
                                json.loads(current_tool["input_raw"])
                                if current_tool["input_raw"]
                                else {}
                            )
                        except json.JSONDecodeError:
                            current_tool["input"] = {}
                        tool_calls.append(current_tool)
                        current_tool = None

        if not tool_calls:
            break

        # Build assistant message with tool_use blocks
        assistant_content: list[dict] = []
        if response_text:
            assistant_content.append({"type": "text", "text": response_text})
        for tc in tool_calls:
            assistant_content.append(
                {
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": tc["input"],
                }
            )
        conversation.append({"role": "assistant", "content": assistant_content})

        # Execute each tool and append results
        tool_results: list[dict] = []
        for tc in tool_calls:
            yield f"data: {json.dumps({'type': 'tool_running', 'name': tc['name'], 'input': tc['input']})}\n\n"
            result_text = await _execute_mcp_tool(tc["name"], tc["input"])
            yield f"data: {json.dumps({'type': 'tool_done', 'name': tc['name']})}\n\n"
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tc["id"],
                    "content": result_text,
                }
            )
        conversation.append({"role": "user", "content": tool_results})

    yield f"data: {json.dumps({'type': 'done'})}\n\n"


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _stream_chat(request.messages),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
