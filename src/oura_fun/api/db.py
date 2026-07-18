"""DuckDB connection for the API layer.

Reads from v_sleep_nightly, v_readiness_daily, v_activity_daily (F2.2 views).
Returns empty lists gracefully when the DB file is absent or views don't exist.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any

_DB_PATH = os.environ.get("OURA_DB_PATH", "oura.duckdb")


@contextmanager
def _conn():
    try:
        import duckdb

        con = duckdb.connect(_DB_PATH, read_only=True)
        try:
            yield con
        finally:
            con.close()
    except Exception:
        yield None


def _query(sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
    with _conn() as con:
        if con is None:
            return []
        try:
            rows = con.execute(sql, params or []).fetchall()
            cols = [d[0] for d in con.description or []]
            return [dict(zip(cols, row)) for row in rows]
        except Exception:
            return []


def list_people() -> list[str]:
    rows = _query("SELECT DISTINCT person_id FROM v_sleep_nightly ORDER BY person_id")
    return [r["person_id"] for r in rows]


def get_sleep(person_id: str, start: str, end: str) -> list[dict[str, Any]]:
    return _query(
        """
        SELECT day, score, total_sleep_duration, rem_sleep_duration,
               deep_sleep_duration, light_sleep_duration, efficiency,
               restless_periods, average_hrv, average_heart_rate
        FROM v_sleep_nightly
        WHERE person_id = ? AND day BETWEEN ? AND ?
        ORDER BY day
        """,
        [person_id, start, end],
    )


def get_readiness(person_id: str, start: str, end: str) -> list[dict[str, Any]]:
    return _query(
        """
        SELECT day, score, temperature_deviation, temperature_trend_deviation,
               hrv_balance_score, recovery_index_score, resting_heart_rate_score,
               sleep_balance_score, previous_night_score, previous_day_score,
               activity_balance_score
        FROM v_readiness_daily
        WHERE person_id = ? AND day BETWEEN ? AND ?
        ORDER BY day
        """,
        [person_id, start, end],
    )


def get_activity(person_id: str, start: str, end: str) -> list[dict[str, Any]]:
    return _query(
        """
        SELECT day, score, active_calories, total_calories, target_calories,
               steps, equivalent_walking_minutes, high_activity_time,
               medium_activity_time, low_activity_time, sedentary_time,
               resting_time, meet_daily_targets, move_every_hour,
               recovery_time, stay_active, training_frequency, training_volume
        FROM v_activity_daily
        WHERE person_id = ? AND day BETWEEN ? AND ?
        ORDER BY day
        """,
        [person_id, start, end],
    )
