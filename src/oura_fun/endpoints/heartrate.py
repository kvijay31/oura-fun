"""Heartrate endpoint wrapper and Pydantic response models.

5-minute granularity samples via GET /v2/usercollection/heartrate.
Uses start_datetime/end_datetime (ISO 8601) rather than date strings —
a different parameter shape from the daily endpoints.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator, Literal

from pydantic import BaseModel

from oura_fun.client import OuraClient

_PATH = "/heartrate"
# heartrate accepts up to 30 days of datetime range per request
_MAX_DAYS = 30


class HeartRateSample(BaseModel):
    """One 5-minute heart-rate sample returned by /v2/usercollection/heartrate."""

    bpm: int
    source: Literal["awake", "rest", "sleep", "session", "live", "background"]
    timestamp: str


def _to_utc_str(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


async def get_heartrate(
    client: OuraClient,
    start: datetime,
    end: datetime,
) -> AsyncIterator[HeartRateSample]:
    """Yield HeartRateSample records for [start, end].

    Splits the range into 30-day windows and follows next_token pagination
    within each window.
    """
    # reuse date_chunks on the date portion, then rebuild datetimes per chunk
    start_date = start.date()
    end_date = end.date()
    for chunk_start_date, chunk_end_date in client.date_chunks(
        start_date, end_date, max_days=_MAX_DAYS
    ):
        # Preserve original times on boundary days; clamp interior chunks
        chunk_start_dt = (
            start if chunk_start_date == start_date else datetime(chunk_start_date.year, chunk_start_date.month, chunk_start_date.day, tzinfo=start.tzinfo)
        )
        chunk_end_dt = (
            end if chunk_end_date == end_date else datetime(chunk_end_date.year, chunk_end_date.month, chunk_end_date.day, 23, 59, 59, tzinfo=end.tzinfo)
        )
        params = {
            "start_datetime": _to_utc_str(chunk_start_dt),
            "end_datetime": _to_utc_str(chunk_end_dt),
        }
        async for raw in client.paginate(_PATH, params):
            yield HeartRateSample.model_validate(raw)
