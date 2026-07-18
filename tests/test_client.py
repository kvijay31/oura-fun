"""Unit tests for OuraClient: pagination, 429 backoff, date chunking."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import httpx
import pytest
import respx

from oura_fun.client import OuraClient

_BASE = "https://api.ouraring.com/v2/usercollection"


@pytest.mark.asyncio
async def test_paginate_single_page():
    with respx.mock(base_url=_BASE) as mock:
        mock.get("/sleep").mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"id": "a"}, {"id": "b"}], "next_token": None},
            )
        )
        async with OuraClient("tok") as client:
            items = [item async for item in client.paginate("/sleep", {})]
    assert items == [{"id": "a"}, {"id": "b"}]


@pytest.mark.asyncio
async def test_paginate_multiple_pages():
    with respx.mock(base_url=_BASE) as mock:
        mock.get("/sleep", params__contains={"next_token": "page2"}).mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"id": "c"}], "next_token": None},
            )
        )
        mock.get("/sleep").mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"id": "a"}, {"id": "b"}], "next_token": "page2"},
            )
        )
        async with OuraClient("tok") as client:
            items = [item async for item in client.paginate("/sleep", {})]
    assert items == [{"id": "a"}, {"id": "b"}, {"id": "c"}]


@pytest.mark.asyncio
async def test_429_backoff_then_success():
    """Client retries on 429 and returns the successful response."""
    call_count = 0

    def side_effect(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(429, headers={"Retry-After": "0"}, json={})
        return httpx.Response(200, json={"data": [{"id": "x"}], "next_token": None})

    with respx.mock(base_url=_BASE) as mock:
        mock.get("/sleep").mock(side_effect=side_effect)
        with patch("asyncio.sleep"):  # don't actually sleep in tests
            async with OuraClient("tok") as client:
                items = [item async for item in client.paginate("/sleep", {})]

    assert items == [{"id": "x"}]
    assert call_count == 2


@pytest.mark.asyncio
async def test_auth_header_injected():
    """Bearer token must appear in the Authorization header."""
    captured_headers: dict = {}

    def side_effect(request: httpx.Request) -> httpx.Response:
        captured_headers.update(dict(request.headers))
        return httpx.Response(200, json={"data": [], "next_token": None})

    with respx.mock(base_url=_BASE) as mock:
        mock.get("/sleep").mock(side_effect=side_effect)
        async with OuraClient("my_token") as client:
            _ = [item async for item in client.paginate("/sleep", {})]

    assert captured_headers.get("authorization") == "Bearer my_token"


def test_date_chunks_single_chunk():
    client = OuraClient.__new__(OuraClient)
    chunks = client.date_chunks(date(2024, 1, 1), date(2024, 1, 15))
    assert chunks == [(date(2024, 1, 1), date(2024, 1, 15))]


def test_date_chunks_exact_boundary():
    client = OuraClient.__new__(OuraClient)
    # 30-day window exactly
    chunks = client.date_chunks(date(2024, 1, 1), date(2024, 1, 30))
    assert chunks == [(date(2024, 1, 1), date(2024, 1, 30))]


def test_date_chunks_splits_at_boundary():
    client = OuraClient.__new__(OuraClient)
    # 31 days → two chunks
    chunks = client.date_chunks(date(2024, 1, 1), date(2024, 1, 31))
    assert len(chunks) == 2
    assert chunks[0] == (date(2024, 1, 1), date(2024, 1, 30))
    assert chunks[1] == (date(2024, 1, 31), date(2024, 1, 31))


def test_date_chunks_large_range():
    client = OuraClient.__new__(OuraClient)
    # Jan 1 - Mar 31 2024 (leap year) = 91 days → 4 chunks (30+30+30+1)
    chunks = client.date_chunks(date(2024, 1, 1), date(2024, 3, 31))
    assert len(chunks) == 4
    assert chunks[0][0] == date(2024, 1, 1)
    assert chunks[-1][1] == date(2024, 3, 31)
    # No chunk exceeds 30 days
    for s, e in chunks:
        assert (e - s).days < 30
