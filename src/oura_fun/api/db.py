"""DuckDB connection for the API layer.

Reads from v_sleep_nightly, v_readiness_daily, v_activity_daily (F2.2 views).
Returns empty lists gracefully when the DB file is absent or views don't exist.
"""

from __future__ import annotations

import datetime
import logging
import os
from contextlib import contextmanager
from typing import Any

_DB_PATH = os.environ.get("OURA_DB_PATH", "oura.duckdb")
_log = logging.getLogger(__name__)


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
        except Exception as exc:
            _log.warning("DB query failed: %s | sql=%s", exc, sql)
            return []


def list_people() -> list[str]:
    rows = _query("SELECT DISTINCT person_id FROM v_sleep_nightly ORDER BY person_id")
    return [r["person_id"] for r in rows]


def get_sleep(person_id: str, start: str, end: str) -> list[dict[str, Any]]:
    # v_sleep_nightly has score + contributors; detailed metrics live in
    # v_sleep_period (per-period). Join on the long_sleep period for nightly view.
    return _query(
        """
        SELECT
            sn.day,
            sn.score,
            sn.c_deep_sleep,
            sn.c_efficiency,
            sn.c_latency,
            sn.c_rem_sleep,
            sn.c_restfulness,
            sn.c_timing,
            sn.c_total_sleep,
            sp.total_sleep_duration,
            sp.rem_sleep_duration,
            sp.deep_sleep_duration,
            sp.light_sleep_duration,
            sp.efficiency,
            sp.restless_periods,
            sp.average_hrv,
            sp.average_heart_rate,
            sp.bedtime_start,
            sp.bedtime_end
        FROM v_sleep_nightly sn
        LEFT JOIN v_sleep_period sp
            ON sp.person_id = sn.person_id
            AND sp.day = sn.day
            AND sp.type = 'long_sleep'
        WHERE sn.person_id = ? AND sn.day BETWEEN ? AND ?
        ORDER BY sn.day
        """,
        [person_id, start, end],
    )


def get_readiness(person_id: str, start: str, end: str) -> list[dict[str, Any]]:
    return _query(
        """
        SELECT
            day,
            score,
            temperature_deviation,
            temperature_trend_deviation,
            c_hrv_balance          AS hrv_balance_score,
            c_recovery_index       AS recovery_index_score,
            c_resting_heart_rate   AS resting_heart_rate_score,
            c_sleep_balance        AS sleep_balance_score,
            c_activity_balance     AS activity_balance_score,
            c_previous_day_activity AS previous_day_score,
            c_previous_night       AS previous_night_score,
            c_body_temperature     AS body_temperature_score
        FROM v_readiness_daily
        WHERE person_id = ? AND day BETWEEN ? AND ?
        ORDER BY day
        """,
        [person_id, start, end],
    )


# Metric catalog: metric_name → (view, column, optional WHERE clause beyond person/date)
# Used by compare_people_metric and get_baseline.
METRIC_CATALOG: dict[str, tuple[str, str, str | None]] = {
    # Sleep scores and contributors (v_sleep_nightly)
    "sleep_score": ("v_sleep_nightly", "score", None),
    "sleep_deep": ("v_sleep_nightly", "c_deep_sleep", None),
    "sleep_efficiency": ("v_sleep_nightly", "c_efficiency", None),
    "sleep_latency": ("v_sleep_nightly", "c_latency", None),
    "sleep_rem": ("v_sleep_nightly", "c_rem_sleep", None),
    "sleep_restfulness": ("v_sleep_nightly", "c_restfulness", None),
    "sleep_timing": ("v_sleep_nightly", "c_timing", None),
    "sleep_total": ("v_sleep_nightly", "c_total_sleep", None),
    # Sleep period detail — long_sleep period only (v_sleep_period)
    "total_sleep_duration": ("v_sleep_period", "total_sleep_duration", "type = 'long_sleep'"),
    "rem_sleep_duration": ("v_sleep_period", "rem_sleep_duration", "type = 'long_sleep'"),
    "deep_sleep_duration": ("v_sleep_period", "deep_sleep_duration", "type = 'long_sleep'"),
    "light_sleep_duration": ("v_sleep_period", "light_sleep_duration", "type = 'long_sleep'"),
    "sleep_efficiency_pct": ("v_sleep_period", "efficiency", "type = 'long_sleep'"),
    "restless_periods": ("v_sleep_period", "restless_periods", "type = 'long_sleep'"),
    "average_hrv": ("v_sleep_period", "average_hrv", "type = 'long_sleep'"),
    "average_heart_rate": ("v_sleep_period", "average_heart_rate", "type = 'long_sleep'"),
    # Readiness (v_readiness_daily)
    "readiness_score": ("v_readiness_daily", "score", None),
    "temperature_deviation": ("v_readiness_daily", "temperature_deviation", None),
    "hrv_balance": ("v_readiness_daily", "c_hrv_balance", None),
    "recovery_index": ("v_readiness_daily", "c_recovery_index", None),
    "resting_heart_rate_score": ("v_readiness_daily", "c_resting_heart_rate", None),
    "sleep_balance": ("v_readiness_daily", "c_sleep_balance", None),
    "activity_balance": ("v_readiness_daily", "c_activity_balance", None),
    # Activity (v_activity_daily)
    "activity_score": ("v_activity_daily", "score", None),
    "steps": ("v_activity_daily", "steps", None),
    "active_calories": ("v_activity_daily", "active_calories", None),
    "total_calories": ("v_activity_daily", "total_calories", None),
    "high_activity_time": ("v_activity_daily", "high_activity_time", None),
    "medium_activity_time": ("v_activity_daily", "medium_activity_time", None),
    "sedentary_time": ("v_activity_daily", "sedentary_time", None),
}


def compare_people_metric(
    metric: str, people: list[str], start: str, end: str
) -> list[dict[str, Any]]:
    """Return daily metric values for multiple people over a date range.

    Each row has ``person_id``, ``day``, ``value``.  Returns ``[]`` for unknown
    metrics or when the DB is unavailable.
    """
    if metric not in METRIC_CATALOG:
        return []
    view, column, extra_filter = METRIC_CATALOG[metric]
    placeholders = ", ".join("?" * len(people))
    where = f"person_id IN ({placeholders}) AND day BETWEEN ? AND ?"
    if extra_filter:
        where += f" AND {extra_filter}"
    sql = (
        f"SELECT person_id, day, {column} AS value"
        f" FROM {view}"
        f" WHERE {where}"
        f" ORDER BY person_id, day"
    )
    return _query(sql, [*people, start, end])


def get_baseline(
    person_id: str, metric: str, window_days: int
) -> dict[str, Any] | None:
    """Return mean and stdev for *metric* over the last *window_days* days.

    Returns ``None`` for unknown metrics or when the DB is unavailable/empty.
    The window end is today; start is ``today - window_days + 1`` days.
    """
    if metric not in METRIC_CATALOG:
        return None
    view, column, extra_filter = METRIC_CATALOG[metric]
    today = datetime.date.today()
    start = str(today - datetime.timedelta(days=window_days - 1))
    end = str(today)
    where = "person_id = ? AND day BETWEEN ? AND ?"
    if extra_filter:
        where += f" AND {extra_filter}"
    sql = (
        f"SELECT"
        f" AVG({column}) AS mean,"
        f" STDDEV_POP({column}) AS stdev,"
        f" COUNT({column}) AS count"
        f" FROM {view}"
        f" WHERE {where}"
    )
    rows = _query(sql, [person_id, start, end])
    if not rows or rows[0]["count"] == 0:
        return None
    row = rows[0]
    return {
        "person": person_id,
        "metric": metric,
        "window_days": window_days,
        "start": start,
        "end": end,
        "mean": row["mean"],
        "stdev": row["stdev"],
        "count": int(row["count"]),
    }


def get_activity(person_id: str, start: str, end: str) -> list[dict[str, Any]]:
    return _query(
        """
        SELECT
            day,
            score,
            active_calories,
            total_calories,
            target_calories,
            steps,
            high_activity_time,
            medium_activity_time,
            low_activity_time,
            sedentary_time,
            resting_time,
            c_meet_daily_targets   AS meet_daily_targets,
            c_move_every_hour      AS move_every_hour,
            c_recovery_time        AS recovery_time,
            c_stay_active          AS stay_active,
            c_training_frequency   AS training_frequency,
            c_training_volume      AS training_volume
        FROM v_activity_daily
        WHERE person_id = ? AND day BETWEEN ? AND ?
        ORDER BY day
        """,
        [person_id, start, end],
    )
