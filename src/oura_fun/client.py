"""F1.1: httpx-based Oura API client with auth, retry, pagination, and date chunking."""

from __future__ import annotations

import time
from datetime import date, timedelta
from typing import Any, Iterator

import httpx

BASE_URL = "https://api.ouraring.com/v2/usercollection"
_MAX_DAYS = 30
_MAX_RETRIES = 5


class OuraClient:
    def __init__(self, token: str, base_url: str = BASE_URL) -> None:
        self._http = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "OuraClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """GET a single page, honouring 429 Retry-After."""
        for attempt in range(_MAX_RETRIES):
            response = self._http.get(path, params=params)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "60"))
                time.sleep(retry_after)
                if attempt == _MAX_RETRIES - 1:
                    response.raise_for_status()
                continue
            response.raise_for_status()
            return response.json()
        return {}  # unreachable, raise_for_status above covers it

    def _paginate(self, path: str, params: dict[str, Any]) -> Iterator[dict[str, Any]]:
        """Yield all items across all next_token pages."""
        current_params = dict(params)
        while True:
            body = self._get(path, current_params)
            yield from body.get("data", [])
            next_token = body.get("next_token")
            if not next_token:
                break
            current_params = {**params, "next_token": next_token}

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def fetch(
        self,
        endpoint: str,
        start_date: date | str,
        end_date: date | str,
        extra_params: dict[str, Any] | None = None,
        chunk: bool = True,
    ) -> list[dict[str, Any]]:
        """Fetch all records for *endpoint* across [start_date, end_date].

        When *chunk* is True (default) the range is split into ≤30-day windows
        so endpoints that enforce that limit are handled transparently.
        """
        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)

        extra = extra_params or {}
        results: list[dict[str, Any]] = []
        path = f"/{endpoint}"

        if not chunk:
            params = {"start_date": str(start_date), "end_date": str(end_date), **extra}
            results.extend(self._paginate(path, params))
            return results

        current = start_date
        while current <= end_date:
            chunk_end = min(current + timedelta(days=_MAX_DAYS - 1), end_date)
            params = {"start_date": str(current), "end_date": str(chunk_end), **extra}
            results.extend(self._paginate(path, params))
            current = chunk_end + timedelta(days=1)

        return results
