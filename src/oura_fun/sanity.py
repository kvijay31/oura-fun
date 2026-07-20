"""F2.6: Sanity checks for ingested Oura data.

Validates:
- No gaps in date sequences across daily endpoints.
- No impossible sleep durations (> 86400 s or negative).
- Logs row counts per raw table per run.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import duckdb

log = logging.getLogger(__name__)

# Daily endpoints keyed by calendar date — we check for gaps in these.
_DAILY_TABLES: list[str] = [
    "raw_daily_sleep",
    "raw_daily_readiness",
    "raw_daily_activity",
    "raw_daily_stress",
    "raw_daily_spo2",
    "raw_sleep_time",
    "raw_sleep",
    "raw_workout",
    "raw_session",
    "raw_enhanced_tag",
]

# Max realistic total sleep duration in seconds (anything above is impossible).
_MAX_SLEEP_SECONDS = 86_400  # 24 h


@dataclass
class SanityResult:
    row_counts: dict[str, int] = field(default_factory=dict)
    # {person_id: {table: [missing_dates]}}
    date_gaps: dict[str, dict[str, list[date]]] = field(default_factory=dict)
    # {person_id: [{natural_key, day, total_sleep_duration}]}
    bad_sleep_durations: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        any_gaps = any(
            dates
            for tables in self.date_gaps.values()
            for dates in tables.values()
        )
        any_bad = any(rows for rows in self.bad_sleep_durations.values())
        return not any_gaps and not any_bad


def row_counts(conn: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Return total row count for every raw endpoint table."""
    from oura_fun.db import ENDPOINT_TABLES

    counts: dict[str, int] = {}
    for table in ENDPOINT_TABLES:
        result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        counts[table] = result[0] if result else 0
    return counts


def _distinct_days(
    conn: duckdb.DuckDBPyConnection, table: str, person_id: str
) -> list[date]:
    """Return sorted list of distinct days present for a person in a table."""
    rows = conn.execute(
        f"SELECT DISTINCT day FROM {table} WHERE person_id = ? ORDER BY day",
        [person_id],
    ).fetchall()
    return [r[0] for r in rows]


def check_date_gaps(
    conn: duckdb.DuckDBPyConnection, person_id: str, table: str
) -> list[date]:
    """Return dates missing from the contiguous range [min_day, max_day] for person."""
    days = _distinct_days(conn, table, person_id)
    if len(days) < 2:
        return []
    missing: list[date] = []
    current = days[0] + timedelta(days=1)
    day_set = set(days)
    while current < days[-1]:
        if current not in day_set:
            missing.append(current)
        current += timedelta(days=1)
    return missing


def check_sleep_durations(
    conn: duckdb.DuckDBPyConnection, person_id: str
) -> list[dict[str, Any]]:
    """Return sleep period rows with impossible total_sleep_duration."""
    rows = conn.execute(
        """
        SELECT natural_key, day, total_sleep_duration
        FROM v_sleep_period
        WHERE person_id = ?
          AND total_sleep_duration IS NOT NULL
          AND (total_sleep_duration > ? OR total_sleep_duration < 0)
        ORDER BY day
        """,
        [person_id, _MAX_SLEEP_SECONDS],
    ).fetchall()
    return [
        {"natural_key": r[0], "day": r[1], "total_sleep_duration": r[2]}
        for r in rows
    ]


def _all_person_ids(conn: duckdb.DuckDBPyConnection) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT person_id FROM raw_daily_sleep ORDER BY person_id"
    ).fetchall()
    return [r[0] for r in rows]


def run_checks(conn: duckdb.DuckDBPyConnection) -> SanityResult:
    """Run all sanity checks and return a SanityResult."""
    result = SanityResult()

    result.row_counts = row_counts(conn)
    log.info("Row counts per table:")
    for table, count in result.row_counts.items():
        log.info("  %-30s %d", table, count)

    persons = _all_person_ids(conn)
    if not persons:
        log.warning("No persons found in raw_daily_sleep — is the DB empty?")
        return result

    for person_id in persons:
        result.date_gaps[person_id] = {}
        for table in _DAILY_TABLES:
            gaps = check_date_gaps(conn, person_id, table)
            if gaps:
                result.date_gaps[person_id][table] = gaps
                log.warning(
                    "Date gaps for %s in %s: %d missing days (%s … %s)",
                    person_id,
                    table,
                    len(gaps),
                    gaps[0],
                    gaps[-1],
                )

        bad = check_sleep_durations(conn, person_id)
        if bad:
            result.bad_sleep_durations[person_id] = bad
            for row in bad:
                log.warning(
                    "Impossible sleep duration for %s: natural_key=%s day=%s duration=%s s",
                    person_id,
                    row["natural_key"],
                    row["day"],
                    row["total_sleep_duration"],
                )

    return result
