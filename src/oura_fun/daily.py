"""F1.2: Endpoint wrappers for daily metric endpoints."""

from __future__ import annotations

from datetime import date

from oura_fun.client import OuraClient
from oura_fun.models import (
    DailyActivity,
    DailyReadiness,
    DailySleep,
    DailySpo2,
    DailyStress,
    SleepTime,
)


def fetch_daily_sleep(
    client: OuraClient,
    start_date: date | str,
    end_date: date | str,
) -> list[DailySleep]:
    records = client.fetch("daily_sleep", start_date, end_date)
    return [DailySleep.model_validate(r) for r in records]


def fetch_daily_readiness(
    client: OuraClient,
    start_date: date | str,
    end_date: date | str,
) -> list[DailyReadiness]:
    records = client.fetch("daily_readiness", start_date, end_date)
    return [DailyReadiness.model_validate(r) for r in records]


def fetch_daily_activity(
    client: OuraClient,
    start_date: date | str,
    end_date: date | str,
) -> list[DailyActivity]:
    records = client.fetch("daily_activity", start_date, end_date)
    return [DailyActivity.model_validate(r) for r in records]


def fetch_daily_stress(
    client: OuraClient,
    start_date: date | str,
    end_date: date | str,
) -> list[DailyStress]:
    records = client.fetch("daily_stress", start_date, end_date)
    return [DailyStress.model_validate(r) for r in records]


def fetch_daily_spo2(
    client: OuraClient,
    start_date: date | str,
    end_date: date | str,
) -> list[DailySpo2]:
    records = client.fetch("daily_spo2", start_date, end_date)
    return [DailySpo2.model_validate(r) for r in records]


def fetch_sleep_time(
    client: OuraClient,
    start_date: date | str,
    end_date: date | str,
) -> list[SleepTime]:
    records = client.fetch("sleep_time", start_date, end_date)
    return [SleepTime.model_validate(r) for r in records]
