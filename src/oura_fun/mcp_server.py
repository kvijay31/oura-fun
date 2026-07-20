"""MCP server for oura-fun.

Exposes v_sleep_nightly, v_readiness_daily, v_activity_daily (F2.2 views)
as MCP tools and provides a data-dictionary resource describing every field.
Never touches the live Oura API — reads DuckDB only.

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
        "Use 'person' to identify whose data to query (e.g. 'kartik'). "
        "Read the oura://data-dictionary resource to understand every field "
        "before writing queries."
    ),
)

# ── F3.4: Data dictionary ─────────────────────────────────────────────────────

_COMMON_FIELDS = {
    "person_id": {
        "type": "TEXT",
        "description": "Internal identifier for the person whose ring generated this data.",
    },
    "natural_key": {
        "type": "TEXT",
        "description": "Unique key derived from the Oura API record id used for deduplication.",
    },
    "day": {
        "type": "DATE",
        "description": "Calendar date (YYYY-MM-DD) the measurement applies to.",
    },
    "fetched_at": {
        "type": "TIMESTAMP",
        "description": "Timestamp when this row was retrieved from the Oura API.",
    },
    "id": {
        "type": "TEXT",
        "description": "Oura API record identifier from the raw JSON payload.",
    },
    "scored_at": {
        "type": "TIMESTAMP",
        "description": "Timestamp when Oura computed the score for this record.",
    },
}

_DATA_DICTIONARY: dict[str, Any] = {
    "description": (
        "Field-level documentation for every DuckDB view in oura-fun. "
        "All views select the latest-fetched row per (person_id, natural_key). "
        "Contributor sub-scores (prefix c_) are 0-100 integers; higher is better. "
        "Time fields in seconds unless otherwise noted."
    ),
    "common_fields": _COMMON_FIELDS,
    "views": {
        "v_sleep_nightly": {
            "source_table": "raw_daily_sleep",
            "description": (
                "One row per person per calendar night. "
                "Oura's daily sleep score and its seven contributor sub-scores."
            ),
            "fields": {
                "score": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": (
                        "Overall sleep quality score. "
                        "≥85 = excellent, 70-84 = good, <70 = needs attention."
                    ),
                },
                "c_deep_sleep": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": (
                        "Rewards a healthy proportion of deep (N3 / slow-wave) sleep. "
                        "Deep sleep drives physical recovery and memory consolidation."
                    ),
                },
                "c_efficiency": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": (
                        "Ratio of time actually asleep to time in bed. "
                        "High efficiency means minimal awake time after lights-out."
                    ),
                },
                "c_latency": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": (
                        "Time taken to fall asleep. "
                        "Optimal is roughly 10-20 min; falling asleep instantly or taking >30 min both reduce this score."
                    ),
                },
                "c_rem_sleep": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": (
                        "Rewards sufficient REM sleep (typically 20-25 % of total). "
                        "REM supports emotional regulation and memory."
                    ),
                },
                "c_restfulness": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": (
                        "Penalizes excessive movement and wake episodes during the night. "
                        "A high score means you slept through without disruption."
                    ),
                },
                "c_timing": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": (
                        "Rewards sleep that aligns with your personal circadian rhythm. "
                        "Sleeping at your body's preferred clock time maximises this score."
                    ),
                },
                "c_total_sleep": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": (
                        "Rewards 7-9 hours of actual sleep. "
                        "Both under- and over-sleeping reduce this score."
                    ),
                },
            },
        },
        "v_readiness_daily": {
            "source_table": "raw_daily_readiness",
            "description": (
                "One row per person per day. "
                "Oura's readiness (recovery) score and eight contributor sub-scores."
            ),
            "fields": {
                "score": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": (
                        "Overall readiness/recovery score for the day. "
                        "≥85 = optimal, 70-84 = good, <70 = take it easy."
                    ),
                },
                "temperature_deviation": {
                    "type": "DOUBLE",
                    "units": "°C",
                    "description": (
                        "Skin temperature deviation from your personal nightly baseline. "
                        "Values outside ±0.5 °C may indicate illness, alcohol use, or unusual exertion."
                    ),
                },
                "temperature_trend_deviation": {
                    "type": "DOUBLE",
                    "units": "°C",
                    "description": (
                        "Multi-day temperature trend deviation from baseline. "
                        "Persistent positive trend alongside illness symptoms warrants attention."
                    ),
                },
                "c_activity_balance": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": (
                        "Measures whether your recent training load is balanced. "
                        "Both too much and too little activity reduce this sub-score."
                    ),
                },
                "c_body_temperature": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": (
                        "Rewards a stable skin temperature near your personal baseline. "
                        "Large deviations in either direction lower the sub-score."
                    ),
                },
                "c_hrv_balance": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": (
                        "Compares last night's HRV to your 3-month trend. "
                        "HRV significantly below your norm signals incomplete recovery."
                    ),
                },
                "c_previous_day_activity": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": (
                        "Scores yesterday's activity level. "
                        "Moderate activity scores best; very high or very low activity reduces it."
                    ),
                },
                "c_previous_night": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": "Reflects the quality of last night's sleep score directly.",
                },
                "c_recovery_index": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": (
                        "How quickly your heart rate settled to its resting level after you fell asleep. "
                        "Rapid stabilisation indicates good cardiovascular recovery."
                    ),
                },
                "c_resting_heart_rate": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": (
                        "Compares current resting HR to your personal baseline. "
                        "Elevated RHR suggests your body is still recovering."
                    ),
                },
                "c_sleep_balance": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": (
                        "Cumulative sleep over the past two weeks vs. your long-term need. "
                        "Persistent sleep debt lowers this even if last night was fine."
                    ),
                },
            },
        },
        "v_activity_daily": {
            "source_table": "raw_daily_activity",
            "description": (
                "One row per person per day. "
                "Oura's activity score, calorie/step metrics, time-in-zone breakdowns, "
                "and six contributor sub-scores."
            ),
            "fields": {
                "score": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": "Overall activity score for the day.",
                },
                "active_calories": {
                    "type": "INTEGER",
                    "units": "kcal",
                    "description": "Calories burned through movement (excludes basal metabolic rate).",
                },
                "total_calories": {
                    "type": "INTEGER",
                    "units": "kcal",
                    "description": "Total calories burned including basal metabolic rate.",
                },
                "target_calories": {
                    "type": "INTEGER",
                    "units": "kcal",
                    "description": "Oura's personalised active-calorie burn target for this day.",
                },
                "steps": {
                    "type": "INTEGER",
                    "description": "Total step count for the day.",
                },
                "equivalent_walking_distance": {
                    "type": "INTEGER",
                    "units": "meters",
                    "description": "Total distance equivalent of all activity converted to walking.",
                },
                "target_meters": {
                    "type": "INTEGER",
                    "units": "meters",
                    "description": "Daily walking-distance target in meters.",
                },
                "meters_to_target": {
                    "type": "INTEGER",
                    "units": "meters",
                    "description": "Remaining meters to reach target_meters (0 if already met).",
                },
                "average_met_minutes": {
                    "type": "DOUBLE",
                    "description": "Average metabolic equivalent minutes for the day.",
                },
                "high_activity_time": {
                    "type": "INTEGER",
                    "units": "seconds",
                    "description": "Time in high-intensity activity (MET > 4, e.g. running).",
                },
                "medium_activity_time": {
                    "type": "INTEGER",
                    "units": "seconds",
                    "description": "Time in medium-intensity activity (e.g. brisk walking).",
                },
                "low_activity_time": {
                    "type": "INTEGER",
                    "units": "seconds",
                    "description": "Time in low-intensity activity (e.g. slow walking).",
                },
                "sedentary_time": {
                    "type": "INTEGER",
                    "units": "seconds",
                    "description": "Time spent sedentary (sitting or standing with minimal movement).",
                },
                "resting_time": {
                    "type": "INTEGER",
                    "units": "seconds",
                    "description": "Time at rest (sleep + very low activity).",
                },
                "non_wear_time": {
                    "type": "INTEGER",
                    "units": "seconds",
                    "description": "Time the ring was detected as not worn.",
                },
                "inactivity_alerts": {
                    "type": "INTEGER",
                    "description": "Number of inactivity-alert triggers during the day.",
                },
                "high_activity_met_minutes": {
                    "type": "DOUBLE",
                    "description": "MET-minutes accumulated from high-intensity activity.",
                },
                "medium_activity_met_minutes": {
                    "type": "DOUBLE",
                    "description": "MET-minutes accumulated from medium-intensity activity.",
                },
                "low_activity_met_minutes": {
                    "type": "DOUBLE",
                    "description": "MET-minutes accumulated from low-intensity activity.",
                },
                "sedentary_met_minutes": {
                    "type": "DOUBLE",
                    "description": "MET-minutes while sedentary.",
                },
                "c_meet_daily_targets": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": "Rewards consistently hitting recent daily activity targets.",
                },
                "c_move_every_hour": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": "Rewards breaking up sedentary time with movement each hour.",
                },
                "c_recovery_time": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": "Rewards adequate low-intensity recovery days after hard training.",
                },
                "c_stay_active": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": "Penalizes long unbroken sedentary stretches during the day.",
                },
                "c_training_frequency": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": "Rewards exercising at least 3 times per week.",
                },
                "c_training_volume": {
                    "type": "INTEGER",
                    "range": "0-100",
                    "description": "Rewards cumulative weekly training volume at an appropriate level.",
                },
            },
        },
        "v_stress_daily": {
            "source_table": "raw_daily_stress",
            "description": (
                "One row per person per day. "
                "Physiological stress and recovery time estimates derived from HRV patterns."
            ),
            "fields": {
                "stress_high": {
                    "type": "INTEGER",
                    "units": "minutes",
                    "description": (
                        "Minutes in a high-stress physiological state "
                        "(elevated sympathetic nervous system activity)."
                    ),
                },
                "recovery_high": {
                    "type": "INTEGER",
                    "units": "minutes",
                    "description": (
                        "Minutes in a high-recovery physiological state "
                        "(elevated parasympathetic activity, associated with rest and repair)."
                    ),
                },
                "day_summary": {
                    "type": "TEXT",
                    "description": (
                        "Oura text summary of the day's stress/recovery balance. "
                        "Values include 'restored', 'normal', 'stressful', 'demanding'."
                    ),
                },
            },
        },
        "v_spo2_daily": {
            "source_table": "raw_daily_spo2",
            "description": (
                "One row per person per day. "
                "Average blood-oxygen saturation during sleep."
            ),
            "fields": {
                "spo2_avg": {
                    "type": "DOUBLE",
                    "units": "%",
                    "description": (
                        "Average blood oxygen saturation (SpO2) during sleep. "
                        "Normal range 95-100 %; below 90 % warrants medical attention."
                    ),
                },
            },
        },
        "v_sleep_period": {
            "source_table": "raw_sleep",
            "description": (
                "One row per sleep period (main night or nap). "
                "Detailed per-period sleep metrics — use for stage durations and biometrics."
            ),
            "fields": {
                "type": {
                    "type": "TEXT",
                    "description": (
                        "Sleep period type: 'long_sleep' (main night), 'short_sleep' (nap), "
                        "'rest', 'late_nap', or 'restless_sleep'."
                    ),
                },
                "bedtime_start": {
                    "type": "TEXT",
                    "description": "ISO 8601 timestamp when the person went to bed.",
                },
                "bedtime_end": {
                    "type": "TEXT",
                    "description": "ISO 8601 timestamp when the person got up.",
                },
                "average_breath": {
                    "type": "DOUBLE",
                    "units": "breaths/min",
                    "description": "Average breathing rate during the sleep period.",
                },
                "average_heart_rate": {
                    "type": "DOUBLE",
                    "units": "bpm",
                    "description": "Average heart rate during the sleep period.",
                },
                "average_hrv": {
                    "type": "INTEGER",
                    "units": "ms (RMSSD)",
                    "description": (
                        "Average heart rate variability during sleep. "
                        "RMSSD metric — higher values indicate stronger parasympathetic (recovery) activity."
                    ),
                },
                "awake_time": {
                    "type": "INTEGER",
                    "units": "seconds",
                    "description": "Time spent awake during the sleep period.",
                },
                "deep_sleep_duration": {
                    "type": "INTEGER",
                    "units": "seconds",
                    "description": "Time in deep (N3 / slow-wave) sleep.",
                },
                "efficiency": {
                    "type": "INTEGER",
                    "units": "%",
                    "description": "Ratio of actual sleep time to time in bed (0-100).",
                },
                "latency": {
                    "type": "INTEGER",
                    "units": "seconds",
                    "description": "Time taken to fall asleep after going to bed.",
                },
                "light_sleep_duration": {
                    "type": "INTEGER",
                    "units": "seconds",
                    "description": "Time in light sleep (N1 + N2 stages combined).",
                },
                "lowest_heart_rate": {
                    "type": "INTEGER",
                    "units": "bpm",
                    "description": "Lowest heart rate recorded during the sleep period.",
                },
                "period_id": {
                    "type": "INTEGER",
                    "description": "Sequential identifier within the night (1 = first/main period).",
                },
                "rem_sleep_duration": {
                    "type": "INTEGER",
                    "units": "seconds",
                    "description": "Time in REM sleep.",
                },
                "restless_periods": {
                    "type": "INTEGER",
                    "description": (
                        "Number of times the person moved significantly enough to disrupt sleep continuity."
                    ),
                },
                "sleep_phase_5_min": {
                    "type": "TEXT",
                    "description": (
                        "5-minute hypnogram encoded as a string of digit characters: "
                        "1=deep, 2=light, 3=REM, 4=awake. "
                        "Length = ceil(total_sleep_duration / 300)."
                    ),
                },
                "movement_30_sec": {
                    "type": "TEXT",
                    "description": "30-second movement signal string used to compute restless_periods.",
                },
                "time_in_bed": {
                    "type": "INTEGER",
                    "units": "seconds",
                    "description": "Total elapsed time between bedtime_start and bedtime_end.",
                },
                "total_sleep_duration": {
                    "type": "INTEGER",
                    "units": "seconds",
                    "description": "Actual sleep time: time_in_bed minus awake_time minus latency.",
                },
            },
        },
        "v_sleep_time": {
            "source_table": "raw_sleep_time",
            "description": (
                "One row per person per day. "
                "Oura's personalised optimal bedtime window recommendation."
            ),
            "fields": {
                "recommendation": {
                    "type": "TEXT",
                    "description": (
                        "Actionable recommendation: 'improve_efficiency', 'earlier_bedtime', "
                        "'later_bedtime', or 'maintain_routine'."
                    ),
                },
                "status": {
                    "type": "TEXT",
                    "description": (
                        "Confidence in the recommendation: 'not_enough_data', 'low', 'medium', 'high'."
                    ),
                },
                "bedtime_day_tz": {
                    "type": "INTEGER",
                    "units": "minutes",
                    "description": "Timezone offset in minutes for interpreting the bedtime offsets.",
                },
                "bedtime_start_offset": {
                    "type": "INTEGER",
                    "units": "seconds from midnight",
                    "description": "Start of recommended bedtime window, in seconds from local midnight.",
                },
                "bedtime_end_offset": {
                    "type": "INTEGER",
                    "units": "seconds from midnight",
                    "description": "End of recommended bedtime window, in seconds from local midnight.",
                },
            },
        },
        "v_heartrate": {
            "source_table": "raw_heartrate",
            "description": (
                "One row per heart-rate measurement (~5-minute granularity). "
                "Covers all sources: sleep, wake, workouts, and live readings."
            ),
            "fields": {
                "timestamp": {
                    "type": "TEXT",
                    "description": "ISO 8601 datetime of this heart-rate sample.",
                },
                "bpm": {
                    "type": "INTEGER",
                    "units": "bpm",
                    "description": "Heart rate in beats per minute.",
                },
                "source": {
                    "type": "TEXT",
                    "description": (
                        "Measurement context: 'awake', 'rest', 'sleep', 'session', 'live', 'background'."
                    ),
                },
            },
        },
        "v_workout": {
            "source_table": "raw_workout",
            "description": (
                "One row per workout. "
                "Includes autodetected and manually logged sessions."
            ),
            "fields": {
                "activity": {
                    "type": "TEXT",
                    "description": (
                        "Workout activity type (e.g. 'running', 'cycling', 'yoga', 'strength_training', "
                        "'walking', 'swimming')."
                    ),
                },
                "start_datetime": {
                    "type": "TEXT",
                    "description": "ISO 8601 timestamp when the workout began.",
                },
                "end_datetime": {
                    "type": "TEXT",
                    "description": "ISO 8601 timestamp when the workout ended.",
                },
                "calories": {
                    "type": "DOUBLE",
                    "units": "kcal",
                    "description": "Estimated calories burned during the workout.",
                },
                "distance": {
                    "type": "DOUBLE",
                    "units": "meters",
                    "description": "Distance covered (null for activities without spatial tracking).",
                },
                "intensity": {
                    "type": "TEXT",
                    "description": "Workout intensity: 'easy', 'moderate', or 'hard'.",
                },
                "label": {
                    "type": "TEXT",
                    "description": "Optional user-provided label for the workout.",
                },
                "source": {
                    "type": "TEXT",
                    "description": (
                        "How the workout was recorded: 'manual', 'autodetected', "
                        "'confirmed', or 'workout_heart_rate'."
                    ),
                },
            },
        },
        "v_session": {
            "source_table": "raw_session",
            "description": (
                "One row per guided session (mindfulness, breathing, nap detection, etc.)."
            ),
            "fields": {
                "type": {
                    "type": "TEXT",
                    "description": (
                        "Session type: 'meditation', 'breathing', 'body_status', "
                        "'stress_monitor', or 'nap_detection'."
                    ),
                },
                "start_datetime": {
                    "type": "TEXT",
                    "description": "ISO 8601 timestamp when the session began.",
                },
                "end_datetime": {
                    "type": "TEXT",
                    "description": "ISO 8601 timestamp when the session ended.",
                },
                "mood": {
                    "type": "TEXT",
                    "description": "Self-reported mood: 'bad', 'worse', 'same', 'good', or 'great'.",
                },
                "perceived_exertion": {
                    "type": "DOUBLE",
                    "range": "0-10",
                    "description": "Subjective effort rating on a 0-10 scale.",
                },
            },
        },
        "v_enhanced_tag": {
            "source_table": "raw_enhanced_tag",
            "description": (
                "One row per user-created tag. "
                "Tags record lifestyle events (caffeine, alcohol, travel, illness, etc.)."
            ),
            "fields": {
                "tag_type_code": {
                    "type": "TEXT",
                    "description": (
                        "Tag category code, e.g. 'tag_generic_nocaffeine', 'tag_travel', "
                        "'tag_alcohol', 'tag_illness', 'tag_generic_other'."
                    ),
                },
                "start_time": {
                    "type": "TEXT",
                    "description": "ISO 8601 timestamp when the tagged event started.",
                },
                "end_time": {
                    "type": "TEXT",
                    "description": "ISO 8601 timestamp when the tagged event ended (null if point-in-time).",
                },
                "start_day": {
                    "type": "TEXT",
                    "description": "Calendar date (YYYY-MM-DD) the tag starts on.",
                },
                "end_day": {
                    "type": "TEXT",
                    "description": "Calendar date (YYYY-MM-DD) the tag ends on.",
                },
                "comment": {
                    "type": "TEXT",
                    "description": "Optional free-text comment attached to the tag.",
                },
                "custom_name": {
                    "type": "TEXT",
                    "description": (
                        "Name of a custom tag type when tag_type_code is 'tag_generic_other'."
                    ),
                },
            },
        },
        "v_personal_info": {
            "source_table": "raw_personal_info",
            "description": (
                "One row per person. "
                "Static profile data from the Oura account."
            ),
            "fields": {
                "age": {
                    "type": "INTEGER",
                    "units": "years",
                    "description": "Person's age at time of last fetch.",
                },
                "weight": {
                    "type": "DOUBLE",
                    "units": "kg",
                    "description": "Person's weight.",
                },
                "height": {
                    "type": "DOUBLE",
                    "units": "meters",
                    "description": "Person's height.",
                },
                "biological_sex": {
                    "type": "TEXT",
                    "description": "Biological sex as recorded in the Oura account: 'male' or 'female'.",
                },
                "email": {
                    "type": "TEXT",
                    "description": "Email address associated with the Oura account.",
                },
            },
        },
    },
}


@mcp.resource(
    "oura://data-dictionary",
    name="data_dictionary",
    description=(
        "Field-level documentation for every DuckDB view exposed by this MCP server. "
        "Covers all views: v_sleep_nightly, v_readiness_daily, v_activity_daily, "
        "v_stress_daily, v_spo2_daily, v_sleep_period, v_sleep_time, v_heartrate, "
        "v_workout, v_session, v_enhanced_tag, v_personal_info. "
        "Read this before writing SQL or interpreting contributor sub-scores."
    ),
    mime_type="application/json",
)
def data_dictionary() -> str:
    """Return the data dictionary as a JSON string."""
    return json.dumps(_DATA_DICTIONARY, indent=2)


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
