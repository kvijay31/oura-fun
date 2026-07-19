"""Chat endpoint — streaming LLM chat with Oura MCP tool access."""

from __future__ import annotations

import json
import os
import statistics
from datetime import date, timedelta
from typing import Any, AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import db

router = APIRouter()

TOOLS: list[dict[str, Any]] = [
    {
        "name": "query_sleep",
        "description": "Query nightly sleep records for a person over a date range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "person": {"type": "string", "description": "Person ID"},
                "start": {"type": "string", "description": "Start date YYYY-MM-DD"},
                "end": {"type": "string", "description": "End date YYYY-MM-DD"},
            },
            "required": ["person", "start", "end"],
        },
    },
    {
        "name": "query_readiness",
        "description": "Query daily readiness records for a person over a date range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "person": {"type": "string", "description": "Person ID"},
                "start": {"type": "string", "description": "Start date YYYY-MM-DD"},
                "end": {"type": "string", "description": "End date YYYY-MM-DD"},
            },
            "required": ["person", "start", "end"],
        },
    },
    {
        "name": "query_activity",
        "description": "Query daily activity records for a person over a date range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "person": {"type": "string", "description": "Person ID"},
                "start": {"type": "string", "description": "Start date YYYY-MM-DD"},
                "end": {"type": "string", "description": "End date YYYY-MM-DD"},
            },
            "required": ["person", "start", "end"],
        },
    },
    {
        "name": "compare_people",
        "description": "Compare a metric across all configured people for a date range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "enum": ["sleep", "readiness", "activity"],
                    "description": "Which metric to compare",
                },
                "start": {"type": "string", "description": "Start date YYYY-MM-DD"},
                "end": {"type": "string", "description": "End date YYYY-MM-DD"},
            },
            "required": ["metric", "start", "end"],
        },
    },
    {
        "name": "baseline",
        "description": (
            "Compute mean and standard deviation of a metric score for a person "
            "over a rolling window of days ending today. Useful for z-scoring."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "person": {"type": "string", "description": "Person ID"},
                "metric": {"type": "string", "enum": ["sleep", "readiness", "activity"]},
                "window": {
                    "type": "integer",
                    "description": "Days to look back (default 90)",
                    "default": 90,
                },
            },
            "required": ["person", "metric"],
        },
    },
    {
        "name": "run_sql",
        "description": (
            "Execute a read-only SELECT query against DuckDB views: "
            "v_sleep_nightly, v_readiness_daily, v_activity_daily. "
            "Only SELECT statements are permitted."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "A SELECT SQL statement"},
            },
            "required": ["query"],
        },
    },
]

def _metric_fetch(metric: str):
    return {"sleep": db.get_sleep, "readiness": db.get_readiness, "activity": db.get_activity}.get(metric)


def execute_tool(name: str, inputs: dict[str, Any]) -> str:
    """Execute a named tool and return JSON string result."""
    try:
        if name == "query_sleep":
            rows = db.get_sleep(inputs["person"], inputs["start"], inputs["end"])
            return json.dumps(rows)

        if name == "query_readiness":
            rows = db.get_readiness(inputs["person"], inputs["start"], inputs["end"])
            return json.dumps(rows)

        if name == "query_activity":
            rows = db.get_activity(inputs["person"], inputs["start"], inputs["end"])
            return json.dumps(rows)

        if name == "compare_people":
            metric = inputs["metric"]
            fetch = _metric_fetch(metric)
            if fetch is None:
                return json.dumps({"error": f"unknown metric {metric!r}"})
            people = db.list_people()
            result = {p: fetch(p, inputs["start"], inputs["end"]) for p in people}
            return json.dumps(result)

        if name == "baseline":
            person = inputs["person"]
            metric = inputs["metric"]
            window = int(inputs.get("window", 90))
            end = date.today()
            start = end - timedelta(days=window)
            fetch = _metric_fetch(metric)
            if fetch is None:
                return json.dumps({"error": f"unknown metric {metric!r}"})
            rows = fetch(person, str(start), str(end))
            scores = [r["score"] for r in rows if r.get("score") is not None]
            if not scores:
                return json.dumps({"person": person, "metric": metric, "window": window, "n": 0, "mean": None, "stdev": None})
            mean = statistics.mean(scores)
            stdev = statistics.stdev(scores) if len(scores) > 1 else 0.0
            return json.dumps({"person": person, "metric": metric, "window": window, "n": len(scores), "mean": round(mean, 2), "stdev": round(stdev, 2)})

        if name == "run_sql":
            query = inputs["query"].strip()
            if not query.upper().lstrip().startswith("SELECT"):
                return json.dumps({"error": "Only SELECT statements are allowed"})
            rows = db._query(query)
            return json.dumps(rows)

        return json.dumps({"error": f"unknown tool {name!r}"})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


class ChatRequest(BaseModel):
    messages: list[dict[str, Any]]


_SYSTEM = (
    "You are a personal health assistant with access to the user's Oura Ring data. "
    "Use the provided tools to fetch and analyse health data when answering. "
    "Today is {today}. "
    "Keep answers concise — lead with the insight, not the raw numbers. "
    "To discover who has data call query_readiness (or similar) for a recent date range."
)


async def _sse_stream(messages: list[dict[str, Any]]) -> AsyncGenerator[str, None]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        yield f"data: {json.dumps({'type': 'error', 'message': 'ANTHROPIC_API_KEY is not configured on the server'})}\n\n"
        return

    model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        system = _SYSTEM.format(today=date.today().isoformat())
        history = list(messages)

        # Agentic loop: run until the model stops calling tools
        while True:
            with client.messages.stream(
                model=model,
                max_tokens=4096,
                system=system,
                messages=history,
                tools=TOOLS,  # type: ignore[arg-type]
            ) as stream:
                accumulated_text = ""

                for event in stream:
                    if event.type == "content_block_delta" and event.delta.type == "text_delta":
                        delta = event.delta.text
                        accumulated_text += delta
                        yield f"data: {json.dumps({'type': 'text', 'delta': delta})}\n\n"

                final = stream.get_final_message()

            # Collect tool-use blocks from the final message
            tool_uses = [b for b in final.content if b.type == "tool_use"]

            if not tool_uses:
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break

            # Append assistant turn (text + tool calls) to history
            assistant_content: list[dict[str, Any]] = []
            if accumulated_text:
                assistant_content.append({"type": "text", "text": accumulated_text})
            for tu in tool_uses:
                assistant_content.append({"type": "tool_use", "id": tu.id, "name": tu.name, "input": tu.input})
            history.append({"role": "assistant", "content": assistant_content})

            # Execute tools and build tool-result turn
            tool_results: list[dict[str, Any]] = []
            for tu in tool_uses:
                yield f"data: {json.dumps({'type': 'tool_call', 'name': tu.name, 'input': tu.input})}\n\n"
                result_json = execute_tool(tu.name, tu.input)
                yield f"data: {json.dumps({'type': 'tool_result', 'name': tu.name})}\n\n"
                tool_results.append({"type": "tool_result", "tool_use_id": tu.id, "content": result_json})

            history.append({"role": "user", "content": tool_results})

    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"


@router.post("/api/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _sse_stream(req.messages),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
