"""F3.1: MCP server scaffold + core query tools.

Exposes v_sleep_nightly, v_readiness_daily, v_activity_daily (F2.2 views)
as MCP tools.  Never touches the live Oura API — reads DuckDB only.

Run with:
    uv run python -m oura_fun.mcp_server
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from oura_fun.api.db import get_activity, get_readiness, get_sleep

mcp = FastMCP(
    name="oura-fun",
    instructions=(
        "Tools for querying personal Oura Ring data stored in DuckDB. "
        "Data is local — no live API calls. "
        "Dates must be YYYY-MM-DD strings. "
        "Use 'person' to identify whose data to query (e.g. 'kartik')."
    ),
)


def _serialise(rows: list[dict[str, Any]]) -> str:
    """Convert rows to a JSON string, formatting dates as strings."""

    def default(obj: Any) -> str:
        return str(obj)

    return json.dumps(rows, default=default, indent=2)


@mcp.tool(
    description=(
        "Query nightly sleep data for a person over a date range. "
        "Returns score, duration, sleep stages (REM/deep/light), efficiency, "
        "restless periods, average HRV, and average heart rate per night."
    )
)
def query_sleep(person: str, start: str, end: str) -> str:
    """Return sleep records for *person* between *start* and *end* (YYYY-MM-DD)."""
    rows = get_sleep(person, start, end)
    if not rows:
        return json.dumps({"person": person, "start": start, "end": end, "records": []})
    return _serialise(rows)


@mcp.tool(
    description=(
        "Query daily readiness data for a person over a date range. "
        "Returns score, temperature deviation, HRV balance, recovery index, "
        "resting heart rate, sleep balance, and contributing sub-scores per day."
    )
)
def query_readiness(person: str, start: str, end: str) -> str:
    """Return readiness records for *person* between *start* and *end* (YYYY-MM-DD)."""
    rows = get_readiness(person, start, end)
    if not rows:
        return json.dumps({"person": person, "start": start, "end": end, "records": []})
    return _serialise(rows)


@mcp.tool(
    description=(
        "Query daily activity data for a person over a date range. "
        "Returns score, active/total/target calories, steps, walking equivalent, "
        "activity time breakdown (high/medium/low/sedentary/resting), "
        "and goal indicators (meet_daily_targets, move_every_hour, etc.) per day."
    )
)
def query_activity(person: str, start: str, end: str) -> str:
    """Return activity records for *person* between *start* and *end* (YYYY-MM-DD)."""
    rows = get_activity(person, start, end)
    if not rows:
        return json.dumps({"person": person, "start": start, "end": end, "records": []})
    return _serialise(rows)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
