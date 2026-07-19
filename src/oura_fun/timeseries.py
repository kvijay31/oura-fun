"""F1.3: Endpoint wrappers for detailed/time-series endpoints."""

from __future__ import annotations

from datetime import date

from oura_fun.client import OuraClient
from oura_fun.models import HeartRateSample, SleepPeriod


def fetch_sleep(
    client: OuraClient,
    start_date: date | str,
    end_date: date | str,
) -> list[SleepPeriod]:
    records = client.fetch("sleep", start_date, end_date)
    return [SleepPeriod.model_validate(r) for r in records]


def fetch_heartrate(
    client: OuraClient,
    start_datetime: str,
    end_datetime: str,
) -> list[HeartRateSample]:
    records = client.fetch_heartrate(start_datetime, end_datetime)
    return [HeartRateSample.model_validate(r) for r in records]
