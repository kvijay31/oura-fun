"""Core HTTP client for the Oura Ring API v2."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any, AsyncIterator

import httpx

_BASE_URL = "https://api.ouraring.com/v2/usercollection"
_MAX_RETRIES = 5


class OuraClient:
    """Async httpx client with bearer auth, 429 backoff, and pagination helpers."""

    def __init__(self, token: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )

    async def __aenter__(self) -> "OuraClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """Single GET with exponential backoff on 429, respecting Retry-After."""
        last_resp: httpx.Response | None = None
        for attempt in range(_MAX_RETRIES):
            resp = await self._client.get(path, params=params)
            last_resp = resp
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", 2**attempt))
                await asyncio.sleep(retry_after)
                continue
            resp.raise_for_status()
            return resp.json()
        raise httpx.HTTPStatusError(
            f"Gave up after {_MAX_RETRIES} retries on {path}",
            request=last_resp.request,  # type: ignore[union-attr]
            response=last_resp,  # type: ignore[arg-type]
        )

    async def paginate(
        self,
        path: str,
        params: dict[str, Any],
    ) -> AsyncIterator[Any]:
        """Yield individual records across all next_token pages."""
        p = dict(params)
        while True:
            body = await self._get(path, p)
            for item in body.get("data", []):
                yield item
            next_token = body.get("next_token")
            if not next_token:
                break
            p["next_token"] = next_token

    def date_chunks(
        self,
        start: date,
        end: date,
        max_days: int = 30,
    ) -> list[tuple[date, date]]:
        """Split [start, end] inclusive into <= max_days windows."""
        chunks: list[tuple[date, date]] = []
        current = start
        while current <= end:
            chunk_end = min(current + timedelta(days=max_days - 1), end)
            chunks.append((current, chunk_end))
            current = chunk_end + timedelta(days=1)
        return chunks
