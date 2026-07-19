"""F2.2: DuckDB derived views — dedup to latest fetched_at, flatten JSON on read."""

from __future__ import annotations

import duckdb

# Each view selects the latest-fetched row per (person_id, natural_key) using a
# window function, then extracts typed columns from the raw JSON payload.
# json_extract_string(payload, '$.path') returns NULL for missing keys, so all
# optional fields are safe to cast with TRY_CAST.

_s = "json_extract_string"
_i = "TRY_CAST(json_extract_string({col}, '{path}') AS INTEGER)"
_f = "TRY_CAST(json_extract_string({col}, '{path}') AS DOUBLE)"


def _dedup_cte(table: str) -> str:
    return f"""WITH _dedup AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY person_id, natural_key
            ORDER BY fetched_at DESC
        ) AS _rn
    FROM {table}
)"""


_VIEW_SQL: dict[str, str] = {
    # ── v_sleep_nightly (daily_sleep scores + contributors) ───────────────
    "v_sleep_nightly": f"""
{_dedup_cte("raw_daily_sleep")}
SELECT
    person_id,
    natural_key,
    day,
    fetched_at,
    json_extract_string(payload, '$.id')                            AS id,
    TRY_CAST(json_extract_string(payload, '$.score') AS INTEGER)   AS score,
    json_extract_string(payload, '$.timestamp')                     AS scored_at,
    TRY_CAST(json_extract_string(payload, '$.contributors.deep_sleep')  AS INTEGER) AS c_deep_sleep,
    TRY_CAST(json_extract_string(payload, '$.contributors.efficiency')  AS INTEGER) AS c_efficiency,
    TRY_CAST(json_extract_string(payload, '$.contributors.latency')     AS INTEGER) AS c_latency,
    TRY_CAST(json_extract_string(payload, '$.contributors.rem_sleep')   AS INTEGER) AS c_rem_sleep,
    TRY_CAST(json_extract_string(payload, '$.contributors.restfulness') AS INTEGER) AS c_restfulness,
    TRY_CAST(json_extract_string(payload, '$.contributors.timing')      AS INTEGER) AS c_timing,
    TRY_CAST(json_extract_string(payload, '$.contributors.total_sleep') AS INTEGER) AS c_total_sleep
FROM _dedup
WHERE _rn = 1
""",

    # ── v_readiness_daily ─────────────────────────────────────────────────
    "v_readiness_daily": f"""
{_dedup_cte("raw_daily_readiness")}
SELECT
    person_id,
    natural_key,
    day,
    fetched_at,
    json_extract_string(payload, '$.id')                                     AS id,
    TRY_CAST(json_extract_string(payload, '$.score') AS INTEGER)             AS score,
    json_extract_string(payload, '$.timestamp')                              AS scored_at,
    TRY_CAST(json_extract_string(payload, '$.temperature_deviation') AS DOUBLE)       AS temperature_deviation,
    TRY_CAST(json_extract_string(payload, '$.temperature_trend_deviation') AS DOUBLE) AS temperature_trend_deviation,
    TRY_CAST(json_extract_string(payload, '$.contributors.activity_balance')    AS INTEGER) AS c_activity_balance,
    TRY_CAST(json_extract_string(payload, '$.contributors.body_temperature')    AS INTEGER) AS c_body_temperature,
    TRY_CAST(json_extract_string(payload, '$.contributors.hrv_balance')         AS INTEGER) AS c_hrv_balance,
    TRY_CAST(json_extract_string(payload, '$.contributors.previous_day_activity') AS INTEGER) AS c_previous_day_activity,
    TRY_CAST(json_extract_string(payload, '$.contributors.previous_night')      AS INTEGER) AS c_previous_night,
    TRY_CAST(json_extract_string(payload, '$.contributors.recovery_index')      AS INTEGER) AS c_recovery_index,
    TRY_CAST(json_extract_string(payload, '$.contributors.resting_heart_rate')  AS INTEGER) AS c_resting_heart_rate,
    TRY_CAST(json_extract_string(payload, '$.contributors.sleep_balance')       AS INTEGER) AS c_sleep_balance
FROM _dedup
WHERE _rn = 1
""",

    # ── v_activity_daily ──────────────────────────────────────────────────
    "v_activity_daily": f"""
{_dedup_cte("raw_daily_activity")}
SELECT
    person_id,
    natural_key,
    day,
    fetched_at,
    json_extract_string(payload, '$.id')                                             AS id,
    TRY_CAST(json_extract_string(payload, '$.score') AS INTEGER)                     AS score,
    json_extract_string(payload, '$.timestamp')                                      AS scored_at,
    TRY_CAST(json_extract_string(payload, '$.active_calories') AS INTEGER)           AS active_calories,
    TRY_CAST(json_extract_string(payload, '$.average_met_minutes') AS DOUBLE)        AS average_met_minutes,
    TRY_CAST(json_extract_string(payload, '$.equivalent_walking_distance') AS INTEGER) AS equivalent_walking_distance,
    TRY_CAST(json_extract_string(payload, '$.high_activity_met_minutes') AS DOUBLE)  AS high_activity_met_minutes,
    TRY_CAST(json_extract_string(payload, '$.high_activity_time') AS INTEGER)        AS high_activity_time,
    TRY_CAST(json_extract_string(payload, '$.inactivity_alerts') AS INTEGER)         AS inactivity_alerts,
    TRY_CAST(json_extract_string(payload, '$.low_activity_met_minutes') AS DOUBLE)   AS low_activity_met_minutes,
    TRY_CAST(json_extract_string(payload, '$.low_activity_time') AS INTEGER)         AS low_activity_time,
    TRY_CAST(json_extract_string(payload, '$.medium_activity_met_minutes') AS DOUBLE) AS medium_activity_met_minutes,
    TRY_CAST(json_extract_string(payload, '$.medium_activity_time') AS INTEGER)      AS medium_activity_time,
    TRY_CAST(json_extract_string(payload, '$.meters_to_target') AS INTEGER)          AS meters_to_target,
    TRY_CAST(json_extract_string(payload, '$.non_wear_time') AS INTEGER)             AS non_wear_time,
    TRY_CAST(json_extract_string(payload, '$.resting_time') AS INTEGER)              AS resting_time,
    TRY_CAST(json_extract_string(payload, '$.sedentary_met_minutes') AS DOUBLE)      AS sedentary_met_minutes,
    TRY_CAST(json_extract_string(payload, '$.sedentary_time') AS INTEGER)            AS sedentary_time,
    TRY_CAST(json_extract_string(payload, '$.steps') AS INTEGER)                     AS steps,
    TRY_CAST(json_extract_string(payload, '$.target_calories') AS INTEGER)           AS target_calories,
    TRY_CAST(json_extract_string(payload, '$.target_meters') AS INTEGER)             AS target_meters,
    TRY_CAST(json_extract_string(payload, '$.total_calories') AS INTEGER)            AS total_calories,
    TRY_CAST(json_extract_string(payload, '$.contributors.meet_daily_targets')   AS INTEGER) AS c_meet_daily_targets,
    TRY_CAST(json_extract_string(payload, '$.contributors.move_every_hour')      AS INTEGER) AS c_move_every_hour,
    TRY_CAST(json_extract_string(payload, '$.contributors.recovery_time')        AS INTEGER) AS c_recovery_time,
    TRY_CAST(json_extract_string(payload, '$.contributors.stay_active')          AS INTEGER) AS c_stay_active,
    TRY_CAST(json_extract_string(payload, '$.contributors.training_frequency')   AS INTEGER) AS c_training_frequency,
    TRY_CAST(json_extract_string(payload, '$.contributors.training_volume')      AS INTEGER) AS c_training_volume
FROM _dedup
WHERE _rn = 1
""",

    # ── v_stress_daily ────────────────────────────────────────────────────
    "v_stress_daily": f"""
{_dedup_cte("raw_daily_stress")}
SELECT
    person_id,
    natural_key,
    day,
    fetched_at,
    json_extract_string(payload, '$.id')                                     AS id,
    TRY_CAST(json_extract_string(payload, '$.stress_high') AS INTEGER)       AS stress_high,
    TRY_CAST(json_extract_string(payload, '$.recovery_high') AS INTEGER)     AS recovery_high,
    json_extract_string(payload, '$.day_summary')                            AS day_summary
FROM _dedup
WHERE _rn = 1
""",

    # ── v_spo2_daily ──────────────────────────────────────────────────────
    "v_spo2_daily": f"""
{_dedup_cte("raw_daily_spo2")}
SELECT
    person_id,
    natural_key,
    day,
    fetched_at,
    json_extract_string(payload, '$.id')                                           AS id,
    TRY_CAST(json_extract_string(payload, '$.spo2_percentage.average') AS DOUBLE)  AS spo2_avg
FROM _dedup
WHERE _rn = 1
""",

    # ── v_sleep_period (per-period sleep detail) ──────────────────────────
    "v_sleep_period": f"""
{_dedup_cte("raw_sleep")}
SELECT
    person_id,
    natural_key,
    day,
    fetched_at,
    json_extract_string(payload, '$.id')                                          AS id,
    json_extract_string(payload, '$.type')                                        AS type,
    json_extract_string(payload, '$.bedtime_start')                               AS bedtime_start,
    json_extract_string(payload, '$.bedtime_end')                                 AS bedtime_end,
    TRY_CAST(json_extract_string(payload, '$.average_breath') AS DOUBLE)          AS average_breath,
    TRY_CAST(json_extract_string(payload, '$.average_heart_rate') AS DOUBLE)      AS average_heart_rate,
    TRY_CAST(json_extract_string(payload, '$.average_hrv') AS INTEGER)            AS average_hrv,
    TRY_CAST(json_extract_string(payload, '$.awake_time') AS INTEGER)             AS awake_time,
    TRY_CAST(json_extract_string(payload, '$.deep_sleep_duration') AS INTEGER)    AS deep_sleep_duration,
    TRY_CAST(json_extract_string(payload, '$.efficiency') AS INTEGER)             AS efficiency,
    TRY_CAST(json_extract_string(payload, '$.latency') AS INTEGER)                AS latency,
    TRY_CAST(json_extract_string(payload, '$.light_sleep_duration') AS INTEGER)   AS light_sleep_duration,
    TRY_CAST(json_extract_string(payload, '$.lowest_heart_rate') AS INTEGER)      AS lowest_heart_rate,
    TRY_CAST(json_extract_string(payload, '$.period_id') AS INTEGER)              AS period_id,
    TRY_CAST(json_extract_string(payload, '$.rem_sleep_duration') AS INTEGER)     AS rem_sleep_duration,
    TRY_CAST(json_extract_string(payload, '$.restless_periods') AS INTEGER)       AS restless_periods,
    json_extract_string(payload, '$.sleep_phase_5_min')                           AS sleep_phase_5_min,
    json_extract_string(payload, '$.movement_30_sec')                             AS movement_30_sec,
    TRY_CAST(json_extract_string(payload, '$.time_in_bed') AS INTEGER)            AS time_in_bed,
    TRY_CAST(json_extract_string(payload, '$.total_sleep_duration') AS INTEGER)   AS total_sleep_duration
FROM _dedup
WHERE _rn = 1
""",

    # ── v_sleep_time (optimal bedtime recommendations) ────────────────────
    "v_sleep_time": f"""
{_dedup_cte("raw_sleep_time")}
SELECT
    person_id,
    natural_key,
    day,
    fetched_at,
    json_extract_string(payload, '$.id')                                              AS id,
    json_extract_string(payload, '$.recommendation')                                  AS recommendation,
    json_extract_string(payload, '$.status')                                          AS status,
    TRY_CAST(json_extract_string(payload, '$.optimal_bedtime.day_tz') AS INTEGER)     AS bedtime_day_tz,
    TRY_CAST(json_extract_string(payload, '$.optimal_bedtime.start_offset') AS INTEGER) AS bedtime_start_offset,
    TRY_CAST(json_extract_string(payload, '$.optimal_bedtime.end_offset') AS INTEGER) AS bedtime_end_offset
FROM _dedup
WHERE _rn = 1
""",

    # ── v_heartrate (5-min HR time series) ───────────────────────────────
    "v_heartrate": f"""
{_dedup_cte("raw_heartrate")}
SELECT
    person_id,
    natural_key,
    day,
    fetched_at,
    json_extract_string(payload, '$.timestamp')              AS timestamp,
    TRY_CAST(json_extract_string(payload, '$.bpm') AS INTEGER) AS bpm,
    json_extract_string(payload, '$.source')                 AS source
FROM _dedup
WHERE _rn = 1
""",

    # ── v_workout ─────────────────────────────────────────────────────────
    "v_workout": f"""
{_dedup_cte("raw_workout")}
SELECT
    person_id,
    natural_key,
    day,
    fetched_at,
    json_extract_string(payload, '$.id')                                  AS id,
    json_extract_string(payload, '$.activity')                            AS activity,
    json_extract_string(payload, '$.start_datetime')                      AS start_datetime,
    json_extract_string(payload, '$.end_datetime')                        AS end_datetime,
    TRY_CAST(json_extract_string(payload, '$.calories') AS DOUBLE)        AS calories,
    TRY_CAST(json_extract_string(payload, '$.distance') AS DOUBLE)        AS distance,
    json_extract_string(payload, '$.intensity')                           AS intensity,
    json_extract_string(payload, '$.label')                               AS label,
    json_extract_string(payload, '$.source')                              AS source
FROM _dedup
WHERE _rn = 1
""",

    # ── v_session ─────────────────────────────────────────────────────────
    "v_session": f"""
{_dedup_cte("raw_session")}
SELECT
    person_id,
    natural_key,
    day,
    fetched_at,
    json_extract_string(payload, '$.id')                                         AS id,
    json_extract_string(payload, '$.type')                                       AS type,
    json_extract_string(payload, '$.start_datetime')                             AS start_datetime,
    json_extract_string(payload, '$.end_datetime')                               AS end_datetime,
    json_extract_string(payload, '$.mood')                                       AS mood,
    TRY_CAST(json_extract_string(payload, '$.perceived_exertion') AS DOUBLE)     AS perceived_exertion
FROM _dedup
WHERE _rn = 1
""",

    # ── v_enhanced_tag ────────────────────────────────────────────────────
    "v_enhanced_tag": f"""
{_dedup_cte("raw_enhanced_tag")}
SELECT
    person_id,
    natural_key,
    day,
    fetched_at,
    json_extract_string(payload, '$.id')                AS id,
    json_extract_string(payload, '$.tag_type_code')     AS tag_type_code,
    json_extract_string(payload, '$.start_time')        AS start_time,
    json_extract_string(payload, '$.end_time')          AS end_time,
    json_extract_string(payload, '$.start_day')         AS start_day,
    json_extract_string(payload, '$.end_day')           AS end_day,
    json_extract_string(payload, '$.comment')           AS comment,
    json_extract_string(payload, '$.custom_name')       AS custom_name
FROM _dedup
WHERE _rn = 1
""",

    # ── v_personal_info ───────────────────────────────────────────────────
    "v_personal_info": f"""
{_dedup_cte("raw_personal_info")}
SELECT
    person_id,
    natural_key,
    day,
    fetched_at,
    json_extract_string(payload, '$.id')                                AS id,
    TRY_CAST(json_extract_string(payload, '$.age') AS INTEGER)          AS age,
    TRY_CAST(json_extract_string(payload, '$.weight') AS DOUBLE)        AS weight,
    TRY_CAST(json_extract_string(payload, '$.height') AS DOUBLE)        AS height,
    json_extract_string(payload, '$.biological_sex')                    AS biological_sex,
    json_extract_string(payload, '$.email')                             AS email
FROM _dedup
WHERE _rn = 1
""",
}

VIEW_NAMES: list[str] = list(_VIEW_SQL.keys())


def create_views(conn: duckdb.DuckDBPyConnection) -> None:
    """Install or replace all derived views in the connected database."""
    for name, sql in _VIEW_SQL.items():
        conn.execute(f"CREATE OR REPLACE VIEW {name} AS {sql}")
