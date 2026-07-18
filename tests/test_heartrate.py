"""Unit tests for the heartrate endpoint wrapper."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
import respx

from oura_fun.client import OuraClient
from oura_fun.endpoints.heartrate import HeartRateSample, get_heartrate

_BASE = "https://api.ouraring.com/v2/usercollection"

_SAMPLE = {
    "bpm": 62,
    "source": "sleep",
    "timestamp": "2024-01-15T02:00:00+00:00",
}


@pytest.mark.asyncio
async def test_get_heartrate_returns_model():
    with respx.mock(base_url=_BASE) as mock:
        mock.get("/heartrate").mock(
            return_value=httpx.Response(
                200,
                json={"data": [_SAMPLE], "next_token": None},
            )
        )
        start = datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 15, 23, 59, tzinfo=timezone.utc)
        async with OuraClient("tok") as client:
            samples = [s async for s in get_heartrate(client, start, end)]

    assert len(samples) == 1
    s = samples[0]
    assert isinstance(s, HeartRateSample)
    assert s.bpm == 62
    assert s.source == "sleep"
    assert s.timestamp == "2024-01-15T02:00:00+00:00"


@pytest.mark.asyncio
async def test_get_heartrate_uses_datetime_params():
    """start_datetime / end_datetime (not start_date) are sent to the API."""
    captured_params: dict = {}

    def side_effect(request: httpx.Request) -> httpx.Response:
        from urllib.parse import parse_qs, urlparse
        parsed = urlparse(str(request.url))
        captured_params.update({k: v[0] for k, v in parse_qs(parsed.query).items()})
        return httpx.Response(200, json={"data": [], "next_token": None})

    with respx.mock(base_url=_BASE) as mock:
        mock.get("/heartrate").mock(side_effect=side_effect)
        start = datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 15, 23, 59, tzinfo=timezone.utc)
        async with OuraClient("tok") as client:
            _ = [s async for s in get_heartrate(client, start, end)]

    assert "start_datetime" in captured_params
    assert "end_datetime" in captured_params
    assert "start_date" not in captured_params


@pytest.mark.asyncio
async def test_get_heartrate_chunks_long_range():
    """A 35-day datetime range issues two separate requests."""
    call_count = 0

    def side_effect(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json={"data": [], "next_token": None})

    with respx.mock(base_url=_BASE) as mock:
        mock.get("/heartrate").mock(side_effect=side_effect)
        start = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 2, 4, 23, 59, tzinfo=timezone.utc)  # 35 days
        async with OuraClient("tok") as client:
            _ = [s async for s in get_heartrate(client, start, end)]

    assert call_count == 2


@pytest.mark.asyncio
async def test_get_heartrate_pagination():
    """next_token is followed within a datetime window."""
    with respx.mock(base_url=_BASE) as mock:
        mock.get("/heartrate", params__contains={"next_token": "hr2"}).mock(
            return_value=httpx.Response(
                200,
                json={"data": [{**_SAMPLE, "bpm": 65}], "next_token": None},
            )
        )
        mock.get("/heartrate").mock(
            return_value=httpx.Response(
                200,
                json={"data": [{**_SAMPLE, "bpm": 60}], "next_token": "hr2"},
            )
        )
        start = datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 15, 23, 59, tzinfo=timezone.utc)
        async with OuraClient("tok") as client:
            samples = [s async for s in get_heartrate(client, start, end)]

    assert [s.bpm for s in samples] == [60, 65]


def test_heartrate_sample_validates():
    s = HeartRateSample.model_validate(_SAMPLE)
    assert s.bpm == 62
    assert s.source == "sleep"
