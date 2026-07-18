"""Sleep endpoint wrapper and Pydantic response models.

Per-period sleep detail (long_sleep, short_sleep, etc.) via
GET /v2/usercollection/sleep with start_date/end_date.
"""

from __future__ import annotations

from datetime import date
from typing import AsyncIterator, Literal

from pydantic import BaseModel

from oura_fun.client import OuraClient

_PATH = "/sleep"


class SleepTimeSeries(BaseModel):
    """Sampled time-series embedded in a sleep period (HRV, HR, movement)."""

    interval: int
    items: list[float | None]
    timestamp: str


class SleepPeriod(BaseModel):
    """One sleep period returned by /v2/usercollection/sleep."""

    id: str
    day: date
    bedtime_start: str
    bedtime_end: str
    type: Literal["long_sleep", "short_sleep", "deleted", "nap"]
    total_sleep_duration: int | None = None
    time_in_bed: int | None = None
    awake_time: int | None = None
    light_sleep_duration: int | None = None
    rem_sleep_duration: int | None = None
    deep_sleep_duration: int | None = None
    efficiency: int | None = None
    latency: int | None = None
    restless_periods: int | None = None
    lowest_heart_rate: int | None = None
    average_heart_rate: float | None = None
    average_breath: float | None = None
    average_hrv: int | None = None
    readiness_score_delta: int | None = None
    sleep_phase_5_min: str | None = None
    movement_30_sec: str | None = None
    low_battery_alert: bool | None = None
    period: int | None = None
    heart_rate: SleepTimeSeries | None = None
    hrv: SleepTimeSeries | None = None


async def get_sleep(
    client: OuraClient,
    start: date,
    end: date,
) -> AsyncIterator[SleepPeriod]:
    """Yield SleepPeriod records for [start, end], chunked to 30-day windows."""
    for chunk_start, chunk_end in client.date_chunks(start, end):
        params = {
            "start_date": chunk_start.isoformat(),
            "end_date": chunk_end.isoformat(),
        }
        async for raw in client.paginate(_PATH, params):
            yield SleepPeriod.model_validate(raw)
