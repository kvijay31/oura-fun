"""Tests for F1.1: OuraClient — pagination, 429 backoff, date-range chunking."""

from __future__ import annotations

import pytest
import respx
import httpx

from oura_fun.client import OuraClient, BASE_URL


TOKEN = "test_token"


def make_client() -> OuraClient:
    return OuraClient(token=TOKEN)


# ── pagination ────────────────────────────────────────────────────────────────

@respx.mock
def test_single_page():
    respx.get(f"{BASE_URL}/daily_sleep").mock(
        return_value=httpx.Response(200, json={"data": [{"id": "a", "day": "2024-01-01"}], "next_token": None})
    )
    client = make_client()
    result = client.fetch("daily_sleep", "2024-01-01", "2024-01-01", chunk=False)
    assert len(result) == 1
    assert result[0]["id"] == "a"
    client.close()


@respx.mock
def test_cursor_pagination_collects_all_pages():
    route = respx.get(f"{BASE_URL}/daily_sleep")
    route.side_effect = [
        httpx.Response(200, json={"data": [{"id": "a", "day": "2024-01-01"}], "next_token": "tok1"}),
        httpx.Response(200, json={"data": [{"id": "b", "day": "2024-01-02"}], "next_token": None}),
    ]
    client = make_client()
    result = client.fetch("daily_sleep", "2024-01-01", "2024-01-31", chunk=False)
    assert [r["id"] for r in result] == ["a", "b"]
    client.close()


@respx.mock
def test_pagination_passes_next_token_as_param():
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if "next_token" not in str(request.url):
            return httpx.Response(200, json={"data": [{"id": "p1"}], "next_token": "tok1"})
        return httpx.Response(200, json={"data": [{"id": "p2"}], "next_token": None})

    respx.get(f"{BASE_URL}/daily_sleep").mock(side_effect=handler)
    client = make_client()
    result = client.fetch("daily_sleep", "2024-01-01", "2024-01-31", chunk=False)
    assert [r["id"] for r in result] == ["p1", "p2"]
    assert "next_token=tok1" in str(calls[1].url)
    client.close()


# ── 429 backoff ───────────────────────────────────────────────────────────────

@respx.mock
def test_429_retries_after_header(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr("oura_fun.client.time.sleep", lambda s: slept.append(s))

    route = respx.get(f"{BASE_URL}/daily_sleep")
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "5"}),
        httpx.Response(200, json={"data": [{"id": "x"}], "next_token": None}),
    ]
    client = make_client()
    result = client.fetch("daily_sleep", "2024-01-01", "2024-01-01", chunk=False)
    assert result[0]["id"] == "x"
    assert slept == [5.0]
    client.close()


@respx.mock
def test_429_uses_default_backoff_when_no_header(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr("oura_fun.client.time.sleep", lambda s: slept.append(s))

    route = respx.get(f"{BASE_URL}/daily_sleep")
    route.side_effect = [
        httpx.Response(429),
        httpx.Response(200, json={"data": [], "next_token": None}),
    ]
    client = make_client()
    client.fetch("daily_sleep", "2024-01-01", "2024-01-01", chunk=False)
    assert slept == [60.0]
    client.close()


# ── date-range chunking ───────────────────────────────────────────────────────

@respx.mock
def test_chunks_long_range_into_30_day_windows():
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"data": [], "next_token": None})

    respx.get(f"{BASE_URL}/daily_sleep").mock(side_effect=handler)
    client = make_client()
    # 2024-01-01 to 2024-03-01 = 61 days → should produce 3 chunks
    client.fetch("daily_sleep", "2024-01-01", "2024-03-01")
    assert len(calls) == 3
    # first window
    assert "start_date=2024-01-01" in str(calls[0].url)
    assert "end_date=2024-01-30" in str(calls[0].url)
    # second window
    assert "start_date=2024-01-31" in str(calls[1].url)
    assert "end_date=2024-02-29" in str(calls[1].url)
    # third window
    assert "start_date=2024-03-01" in str(calls[2].url)
    assert "end_date=2024-03-01" in str(calls[2].url)
    client.close()


@respx.mock
def test_no_chunk_sends_single_request():
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"data": [], "next_token": None})

    respx.get(f"{BASE_URL}/daily_sleep").mock(side_effect=handler)
    client = make_client()
    client.fetch("daily_sleep", "2024-01-01", "2024-03-01", chunk=False)
    assert len(calls) == 1
    client.close()


# ── bearer auth ───────────────────────────────────────────────────────────────

@respx.mock
def test_bearer_token_injected():
    received_auth: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        received_auth.append(request.headers.get("authorization", ""))
        return httpx.Response(200, json={"data": [], "next_token": None})

    respx.get(f"{BASE_URL}/daily_sleep").mock(side_effect=handler)
    client = make_client()
    client.fetch("daily_sleep", "2024-01-01", "2024-01-01", chunk=False)
    assert received_auth[0] == f"Bearer {TOKEN}"
    client.close()


# ── context manager ───────────────────────────────────────────────────────────

@respx.mock
def test_context_manager():
    respx.get(f"{BASE_URL}/daily_sleep").mock(
        return_value=httpx.Response(200, json={"data": [], "next_token": None})
    )
    with OuraClient(TOKEN) as client:
        result = client.fetch("daily_sleep", "2024-01-01", "2024-01-01", chunk=False)
    assert result == []
