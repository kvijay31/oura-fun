"""DuckDB connection for the API layer.

Reads from v_sleep_nightly, v_readiness_daily, v_activity_daily (F2.2 views).
Returns empty lists gracefully when the DB file is absent or views don't exist.
"""

from __future__ import annotations

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


def run_sql(query: str) -> list[dict[str, Any]]:
    """Execute *query* against the read-only DuckDB views.

    Callers are responsible for validating that *query* is a SELECT/WITH statement.
    The DuckDB connection is opened read_only=True as a second layer of enforcement.
    """
    return _query(query)


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
