"""F1.2: Pydantic response models for daily metric endpoints."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


# ── daily_sleep ──────────────────────────────────────────────────────────────

class SleepContributors(BaseModel):
    deep_sleep: Optional[int] = None
    efficiency: Optional[int] = None
    latency: Optional[int] = None
    rem_sleep: Optional[int] = None
    restfulness: Optional[int] = None
    timing: Optional[int] = None
    total_sleep: Optional[int] = None


class DailySleep(BaseModel):
    id: str
    day: str
    score: Optional[int] = None
    timestamp: Optional[str] = None
    contributors: Optional[SleepContributors] = None


# ── daily_readiness ───────────────────────────────────────────────────────────

class ReadinessContributors(BaseModel):
    activity_balance: Optional[int] = None
    body_temperature: Optional[int] = None
    hrv_balance: Optional[int] = None
    previous_day_activity: Optional[int] = None
    previous_night: Optional[int] = None
    recovery_index: Optional[int] = None
    resting_heart_rate: Optional[int] = None
    sleep_balance: Optional[int] = None


class DailyReadiness(BaseModel):
    id: str
    day: str
    score: Optional[int] = None
    timestamp: Optional[str] = None
    temperature_deviation: Optional[float] = None
    temperature_trend_deviation: Optional[float] = None
    contributors: Optional[ReadinessContributors] = None


# ── daily_activity ────────────────────────────────────────────────────────────

class ActivityContributors(BaseModel):
    meet_daily_targets: Optional[int] = None
    move_every_hour: Optional[int] = None
    recovery_time: Optional[int] = None
    stay_active: Optional[int] = None
    training_frequency: Optional[int] = None
    training_volume: Optional[int] = None


class DailyActivity(BaseModel):
    id: str
    day: str
    score: Optional[int] = None
    timestamp: Optional[str] = None
    active_calories: Optional[int] = None
    average_met_minutes: Optional[float] = None
    equivalent_walking_distance: Optional[int] = None
    high_activity_met_minutes: Optional[float] = None
    high_activity_time: Optional[int] = None
    inactivity_alerts: Optional[int] = None
    low_activity_met_minutes: Optional[float] = None
    low_activity_time: Optional[int] = None
    medium_activity_met_minutes: Optional[float] = None
    medium_activity_time: Optional[int] = None
    meters_to_target: Optional[int] = None
    non_wear_time: Optional[int] = None
    resting_time: Optional[int] = None
    sedentary_met_minutes: Optional[float] = None
    sedentary_time: Optional[int] = None
    steps: Optional[int] = None
    target_calories: Optional[int] = None
    target_meters: Optional[int] = None
    total_calories: Optional[int] = None
    contributors: Optional[ActivityContributors] = None


# ── daily_stress ──────────────────────────────────────────────────────────────

class DailyStress(BaseModel):
    id: str
    day: str
    stress_high: Optional[int] = None
    recovery_high: Optional[int] = None
    day_summary: Optional[str] = None


# ── daily_spo2 ────────────────────────────────────────────────────────────────

class Spo2Percentage(BaseModel):
    average: Optional[float] = None


class DailySpo2(BaseModel):
    id: str
    day: str
    spo2_percentage: Optional[Spo2Percentage] = None


# ── sleep_time ────────────────────────────────────────────────────────────────

class OptimalBedtime(BaseModel):
    day_tz: Optional[int] = None
    end_offset: Optional[int] = None
    start_offset: Optional[int] = None


class SleepTime(BaseModel):
    id: str
    day: str
    optimal_bedtime: Optional[OptimalBedtime] = None
    recommendation: Optional[str] = None
    status: Optional[str] = None


# ── F1.4: events & metadata ───────────────────────────────────────────────────

class Workout(BaseModel):
    id: str
    day: str
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    activity: Optional[str] = None
    calories: Optional[float] = None
    distance: Optional[float] = None
    intensity: Optional[str] = None
    label: Optional[str] = None
    source: Optional[str] = None


class TimeSeriesSamples(BaseModel):
    interval: Optional[float] = None
    items: Optional[list[Optional[float]]] = None
    timestamp: Optional[str] = None


class Session(BaseModel):
    id: str
    day: str
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    type: Optional[str] = None
    heart_rate: Optional[TimeSeriesSamples] = None
    heart_rate_variance: Optional[TimeSeriesSamples] = None
    mood: Optional[str] = None
    perceived_exertion: Optional[float] = None


class EnhancedTag(BaseModel):
    id: str
    tag_type_code: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    start_day: Optional[str] = None
    end_day: Optional[str] = None
    comment: Optional[str] = None
    custom_name: Optional[str] = None


class PersonalInfo(BaseModel):
    id: str
    age: Optional[int] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    biological_sex: Optional[str] = None
    email: Optional[str] = None
