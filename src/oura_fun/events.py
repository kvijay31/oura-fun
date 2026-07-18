"""F1.4: Endpoint wrappers for events & metadata endpoints."""

from __future__ import annotations

from datetime import date

from oura_fun.client import OuraClient
from oura_fun.models import EnhancedTag, PersonalInfo, Session, Workout


def fetch_workout(
    client: OuraClient,
    start_date: date | str,
    end_date: date | str,
) -> list[Workout]:
    records = client.fetch("workout", start_date, end_date)
    return [Workout.model_validate(r) for r in records]


def fetch_session(
    client: OuraClient,
    start_date: date | str,
    end_date: date | str,
) -> list[Session]:
    records = client.fetch("session", start_date, end_date)
    return [Session.model_validate(r) for r in records]


def fetch_enhanced_tag(
    client: OuraClient,
    start_date: date | str,
    end_date: date | str,
) -> list[EnhancedTag]:
    records = client.fetch("enhanced_tag", start_date, end_date)
    return [EnhancedTag.model_validate(r) for r in records]


def fetch_personal_info(client: OuraClient) -> PersonalInfo:
    """Fetch personal info (single-record, no date range)."""
    record = client.get_one("personal_info")
    return PersonalInfo.model_validate(record)
