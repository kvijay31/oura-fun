"""DuckDB view SQL for F9.2.

These views are created at API startup (CREATE VIEW IF NOT EXISTS) over the
raw tables from F2.1. Each view deduplicates to the latest fetched_at per
(person_id, day) and flattens the JSON payload into typed scalar columns.
"""
from __future__ import annotations

SLEEP_VIEW_SQL = """\
CREATE VIEW IF NOT EXISTS v_sleep_nightly AS
WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY person_id, day ORDER BY fetched_at DESC
        ) AS rn
    FROM raw_daily_sleep
)
SELECT
    person_id,
    day,
    json_extract_string(payload, '$.id')                                        AS id,
    TRY_CAST(json_extract_string(payload, '$.score') AS INTEGER)                AS score,
    TRY_CAST(json_extract_string(payload, '$.contributors.deep_sleep')
             AS INTEGER)                                                        AS deep_sleep_score,
    TRY_CAST(json_extract_string(payload, '$.contributors.efficiency')
             AS INTEGER)                                                        AS efficiency_score,
    TRY_CAST(json_extract_string(payload, '$.contributors.latency')
             AS INTEGER)                                                        AS latency_score,
    TRY_CAST(json_extract_string(payload, '$.contributors.rem_sleep')
             AS INTEGER)                                                        AS rem_sleep_score,
    TRY_CAST(json_extract_string(payload, '$.contributors.restfulness')
             AS INTEGER)                                                        AS restfulness_score,
    TRY_CAST(json_extract_string(payload, '$.contributors.timing')
             AS INTEGER)                                                        AS timing_score,
    TRY_CAST(json_extract_string(payload, '$.contributors.total_sleep')
             AS INTEGER)                                                        AS total_sleep_score
FROM ranked
WHERE rn = 1
"""

READINESS_VIEW_SQL = """\
CREATE VIEW IF NOT EXISTS v_readiness_daily AS
WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY person_id, day ORDER BY fetched_at DESC
        ) AS rn
    FROM raw_daily_readiness
)
SELECT
    person_id,
    day,
    json_extract_string(payload, '$.id')                                               AS id,
    TRY_CAST(json_extract_string(payload, '$.score') AS INTEGER)                       AS score,
    TRY_CAST(json_extract_string(payload, '$.temperature_deviation') AS DOUBLE)        AS temperature_deviation,
    TRY_CAST(json_extract_string(payload, '$.temperature_trend_deviation') AS DOUBLE)  AS temperature_trend_deviation,
    TRY_CAST(json_extract_string(payload, '$.contributors.activity_balance')
             AS INTEGER)                                                               AS activity_balance_score,
    TRY_CAST(json_extract_string(payload, '$.contributors.body_temperature')
             AS INTEGER)                                                               AS body_temperature_score,
    TRY_CAST(json_extract_string(payload, '$.contributors.hrv_balance')
             AS INTEGER)                                                               AS hrv_balance_score,
    TRY_CAST(json_extract_string(payload, '$.contributors.previous_day_activity')
             AS INTEGER)                                                               AS previous_day_activity_score,
    TRY_CAST(json_extract_string(payload, '$.contributors.previous_night')
             AS INTEGER)                                                               AS previous_night_score,
    TRY_CAST(json_extract_string(payload, '$.contributors.recovery_index')
             AS INTEGER)                                                               AS recovery_index_score,
    TRY_CAST(json_extract_string(payload, '$.contributors.resting_heart_rate')
             AS INTEGER)                                                               AS resting_heart_rate_score,
    TRY_CAST(json_extract_string(payload, '$.contributors.sleep_balance')
             AS INTEGER)                                                               AS sleep_balance_score
FROM ranked
WHERE rn = 1
"""

ACTIVITY_VIEW_SQL = """\
CREATE VIEW IF NOT EXISTS v_activity_daily AS
WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY person_id, day ORDER BY fetched_at DESC
        ) AS rn
    FROM raw_daily_activity
)
SELECT
    person_id,
    day,
    json_extract_string(payload, '$.id')                                              AS id,
    TRY_CAST(json_extract_string(payload, '$.score') AS INTEGER)                      AS score,
    TRY_CAST(json_extract_string(payload, '$.active_calories') AS INTEGER)            AS active_calories,
    TRY_CAST(json_extract_string(payload, '$.steps') AS INTEGER)                      AS steps,
    TRY_CAST(json_extract_string(payload, '$.equivalent_walking_distance') AS INTEGER) AS equivalent_walking_distance,
    TRY_CAST(json_extract_string(payload, '$.high_activity_time') AS INTEGER)         AS high_activity_time,
    TRY_CAST(json_extract_string(payload, '$.medium_activity_time') AS INTEGER)       AS medium_activity_time,
    TRY_CAST(json_extract_string(payload, '$.low_activity_time') AS INTEGER)          AS low_activity_time,
    TRY_CAST(json_extract_string(payload, '$.non_wear_time') AS INTEGER)              AS non_wear_time,
    TRY_CAST(json_extract_string(payload, '$.inactivity_alerts') AS INTEGER)          AS inactivity_alerts,
    TRY_CAST(json_extract_string(payload, '$.total_calories') AS INTEGER)             AS total_calories,
    TRY_CAST(json_extract_string(payload, '$.contributors.meet_daily_targets')
             AS INTEGER)                                                              AS meet_daily_targets_score,
    TRY_CAST(json_extract_string(payload, '$.contributors.move_every_hour')
             AS INTEGER)                                                              AS move_every_hour_score,
    TRY_CAST(json_extract_string(payload, '$.contributors.recovery_time')
             AS INTEGER)                                                              AS recovery_time_score,
    TRY_CAST(json_extract_string(payload, '$.contributors.stay_active')
             AS INTEGER)                                                              AS stay_active_score,
    TRY_CAST(json_extract_string(payload, '$.contributors.training_frequency')
             AS INTEGER)                                                              AS training_frequency_score,
    TRY_CAST(json_extract_string(payload, '$.contributors.training_volume')
             AS INTEGER)                                                              AS training_volume_score
FROM ranked
WHERE rn = 1
"""

VIEW_SQLS: list[str] = [SLEEP_VIEW_SQL, READINESS_VIEW_SQL, ACTIVITY_VIEW_SQL]
