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

from oura_fun.api.db import (
    METRIC_CATALOG,
    compare_people_metric,
    get_activity,
    get_baseline,
    get_readiness,
    get_sleep,
)

mcp = FastMCP(
    name="oura-fun",
    instructions=(
        "Tools for querying personal Oura Ring data stored in DuckDB. "
        "Data is local — no live API calls. "
        "Dates must be YYYY-MM-DD strings. "
        "Use 'person' to identify whose data to query (e.g. 'kartik')."
    ),
)


def _serialise(data: list[dict[str, Any]] | dict[str, Any]) -> str:
    """Convert rows or a single record to a JSON string, formatting dates as strings."""

    def default(obj: Any) -> str:
        return str(obj)

    return json.dumps(data, default=default, indent=2)


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


_METRIC_NAMES = ", ".join(sorted(METRIC_CATALOG))


@mcp.tool(
    description=(
        "Compare a metric across multiple people over a date range. "
        f"Supported metrics: {_METRIC_NAMES}. "
        "'people' is a comma-separated list of person IDs (e.g. 'kartik,partner'). "
        "Returns a list of {person_id, day, value} records ordered by person then date."
    )
)
def compare_people(metric: str, people: str, start: str, end: str) -> str:
    """Return *metric* values for each person in the comma-separated *people* list."""
    person_list = [p.strip() for p in people.split(",") if p.strip()]
    if not person_list:
        return json.dumps({"error": "No people specified."})
    if metric not in METRIC_CATALOG:
        return json.dumps(
            {
                "error": f"Unknown metric '{metric}'.",
                "supported_metrics": sorted(METRIC_CATALOG),
            }
        )
    rows = compare_people_metric(metric, person_list, start, end)
    if not rows:
        return json.dumps(
            {"metric": metric, "people": person_list, "start": start, "end": end, "records": []}
        )
    return _serialise(rows)


@mcp.tool(
    description=(
        "Compute mean and standard deviation for a metric over a trailing window "
        "of days, for use in z-scoring. "
        f"Supported metrics: {_METRIC_NAMES}. "
        "'window' is the number of calendar days to look back (e.g. 90). "
        "Returns {person, metric, window_days, start, end, mean, stdev, count}."
    )
)
def baseline(person: str, metric: str, window: int) -> str:
    """Return mean and stdev for *metric* over the last *window* days for *person*."""
    if metric not in METRIC_CATALOG:
        return json.dumps(
            {
                "error": f"Unknown metric '{metric}'.",
                "supported_metrics": sorted(METRIC_CATALOG),
            }
        )
    if window < 1:
        return json.dumps({"error": "window must be a positive integer."})
    result = get_baseline(person, metric, window)
    if result is None:
        return json.dumps(
            {"person": person, "metric": metric, "window_days": window, "mean": None, "stdev": None, "count": 0}
        )
    return _serialise(result)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
