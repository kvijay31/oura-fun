"""Pydantic response models for the F9.2 API layer.

Shape mirrors F3.1's MCP tool query results so dashboard and chat agree on
what a record looks like.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


class SleepContributors(BaseModel):
    deep_sleep: Optional[int] = None
    efficiency: Optional[int] = None
    latency: Optional[int] = None
    rem_sleep: Optional[int] = None
    restfulness: Optional[int] = None
    timing: Optional[int] = None
    total_sleep: Optional[int] = None


class SleepRecord(BaseModel):
    day: date
    score: Optional[int] = None
    contributors: Optional[SleepContributors] = None

    @classmethod
    def from_row(cls, row: dict) -> "SleepRecord":
        contribs = SleepContributors(
            deep_sleep=row.get("deep_sleep_score"),
            efficiency=row.get("efficiency_score"),
            latency=row.get("latency_score"),
            rem_sleep=row.get("rem_sleep_score"),
            restfulness=row.get("restfulness_score"),
            timing=row.get("timing_score"),
            total_sleep=row.get("total_sleep_score"),
        )
        return cls(
            day=row["day"],
            score=row.get("score"),
            contributors=contribs if any(v is not None for v in contribs.model_dump().values()) else None,
        )


class SleepResponse(BaseModel):
    person_id: str
    records: list[SleepRecord]


class ReadinessContributors(BaseModel):
    activity_balance: Optional[int] = None
    body_temperature: Optional[int] = None
    hrv_balance: Optional[int] = None
    previous_day_activity: Optional[int] = None
    previous_night: Optional[int] = None
    recovery_index: Optional[int] = None
    resting_heart_rate: Optional[int] = None
    sleep_balance: Optional[int] = None


class ReadinessRecord(BaseModel):
    day: date
    score: Optional[int] = None
    temperature_deviation: Optional[float] = None
    temperature_trend_deviation: Optional[float] = None
    contributors: Optional[ReadinessContributors] = None

    @classmethod
    def from_row(cls, row: dict) -> "ReadinessRecord":
        contribs = ReadinessContributors(
            activity_balance=row.get("activity_balance_score"),
            body_temperature=row.get("body_temperature_score"),
            hrv_balance=row.get("hrv_balance_score"),
            previous_day_activity=row.get("previous_day_activity_score"),
            previous_night=row.get("previous_night_score"),
            recovery_index=row.get("recovery_index_score"),
            resting_heart_rate=row.get("resting_heart_rate_score"),
            sleep_balance=row.get("sleep_balance_score"),
        )
        return cls(
            day=row["day"],
            score=row.get("score"),
            temperature_deviation=row.get("temperature_deviation"),
            temperature_trend_deviation=row.get("temperature_trend_deviation"),
            contributors=contribs if any(v is not None for v in contribs.model_dump().values()) else None,
        )


class ReadinessResponse(BaseModel):
    person_id: str
    records: list[ReadinessRecord]


class ActivityContributors(BaseModel):
    meet_daily_targets: Optional[int] = None
    move_every_hour: Optional[int] = None
    recovery_time: Optional[int] = None
    stay_active: Optional[int] = None
    training_frequency: Optional[int] = None
    training_volume: Optional[int] = None


class ActivityRecord(BaseModel):
    day: date
    score: Optional[int] = None
    active_calories: Optional[int] = None
    steps: Optional[int] = None
    equivalent_walking_distance: Optional[int] = None
    high_activity_time: Optional[int] = None
    medium_activity_time: Optional[int] = None
    low_activity_time: Optional[int] = None
    non_wear_time: Optional[int] = None
    inactivity_alerts: Optional[int] = None
    total_calories: Optional[int] = None
    contributors: Optional[ActivityContributors] = None

    @classmethod
    def from_row(cls, row: dict) -> "ActivityRecord":
        contribs = ActivityContributors(
            meet_daily_targets=row.get("meet_daily_targets_score"),
            move_every_hour=row.get("move_every_hour_score"),
            recovery_time=row.get("recovery_time_score"),
            stay_active=row.get("stay_active_score"),
            training_frequency=row.get("training_frequency_score"),
            training_volume=row.get("training_volume_score"),
        )
        return cls(
            day=row["day"],
            score=row.get("score"),
            active_calories=row.get("active_calories"),
            steps=row.get("steps"),
            equivalent_walking_distance=row.get("equivalent_walking_distance"),
            high_activity_time=row.get("high_activity_time"),
            medium_activity_time=row.get("medium_activity_time"),
            low_activity_time=row.get("low_activity_time"),
            non_wear_time=row.get("non_wear_time"),
            inactivity_alerts=row.get("inactivity_alerts"),
            total_calories=row.get("total_calories"),
            contributors=contribs if any(v is not None for v in contribs.model_dump().values()) else None,
        )


class ActivityResponse(BaseModel):
    person_id: str
    records: list[ActivityRecord]


class PeopleResponse(BaseModel):
    people: list[str]
