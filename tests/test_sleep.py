"""Unit tests for the sleep endpoint wrapper."""

from __future__ import annotations

from datetime import date

import httpx
import pytest
import respx

from oura_fun.client import OuraClient
from oura_fun.endpoints.sleep import SleepPeriod, get_sleep

_BASE = "https://api.ouraring.com/v2/usercollection"

_SAMPLE_PERIOD = {
    "id": "abc123",
    "day": "2024-01-15",
    "bedtime_start": "2024-01-14T23:00:00+00:00",
    "bedtime_end": "2024-01-15T07:00:00+00:00",
    "type": "long_sleep",
    "total_sleep_duration": 25200,
    "time_in_bed": 28800,
    "awake_time": 1800,
    "light_sleep_duration": 10800,
    "rem_sleep_duration": 5400,
    "deep_sleep_duration": 7200,
    "efficiency": 87,
    "latency": 420,
    "restless_periods": 3,
    "lowest_heart_rate": 48,
    "average_heart_rate": 55.2,
    "average_breath": 14.8,
    "average_hrv": 47,
    "readiness_score_delta": 2,
    "sleep_phase_5_min": "444412222",
    "movement_30_sec": "111112233",
    "low_battery_alert": False,
    "period": 0,
}


@pytest.mark.asyncio
async def test_get_sleep_returns_model():
    with respx.mock(base_url=_BASE) as mock:
        mock.get("/sleep").mock(
            return_value=httpx.Response(
                200,
                json={"data": [_SAMPLE_PERIOD], "next_token": None},
            )
        )
        async with OuraClient("tok") as client:
            periods = [p async for p in get_sleep(client, date(2024, 1, 1), date(2024, 1, 15))]

    assert len(periods) == 1
    p = periods[0]
    assert isinstance(p, SleepPeriod)
    assert p.id == "abc123"
    assert p.day == date(2024, 1, 15)
    assert p.type == "long_sleep"
    assert p.efficiency == 87
    assert p.average_hrv == 47


@pytest.mark.asyncio
async def test_get_sleep_chunks_long_range():
    """A range >30 days issues multiple chunked requests."""
    call_count = 0

    def side_effect(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json={"data": [], "next_token": None})

    with respx.mock(base_url=_BASE) as mock:
        mock.get("/sleep").mock(side_effect=side_effect)
        async with OuraClient("tok") as client:
            # Jan 1 - Mar 1 2024 (leap year) = 61 days → 3 chunks
            _ = [p async for p in get_sleep(client, date(2024, 1, 1), date(2024, 3, 1))]

    assert call_count == 3


@pytest.mark.asyncio
async def test_get_sleep_pagination():
    """next_token is followed within a single date window."""
    with respx.mock(base_url=_BASE) as mock:
        mock.get("/sleep", params__contains={"next_token": "tok2"}).mock(
            return_value=httpx.Response(
                200,
                json={"data": [{**_SAMPLE_PERIOD, "id": "p2"}], "next_token": None},
            )
        )
        mock.get("/sleep").mock(
            return_value=httpx.Response(
                200,
                json={"data": [{**_SAMPLE_PERIOD, "id": "p1"}], "next_token": "tok2"},
            )
        )
        async with OuraClient("tok") as client:
            periods = [p async for p in get_sleep(client, date(2024, 1, 1), date(2024, 1, 15))]

    assert [p.id for p in periods] == ["p1", "p2"]


def test_sleep_period_optional_fields():
    """Model validates with only required fields present."""
    minimal = {
        "id": "x",
        "day": "2024-01-01",
        "bedtime_start": "2024-01-01T00:00:00Z",
        "bedtime_end": "2024-01-01T08:00:00Z",
        "type": "nap",
    }
    p = SleepPeriod.model_validate(minimal)
    assert p.efficiency is None
    assert p.average_hrv is None
