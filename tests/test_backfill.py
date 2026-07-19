"""Tests for F2.3: backfill script."""

from __future__ import annotations

import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import duckdb
import pytest

from oura_fun.db import init_schema
from scripts.backfill import _day_for, _insert_records, backfill_person, main


@pytest.fixture()
def conn():
    c = duckdb.connect(":memory:")
    init_schema(c)
    yield c
    c.close()


FETCHED = datetime(2025, 1, 15, 12, 0, 0)


# ── _day_for ──────────────────────────────────────────────────────────────────

def test_day_for_regular_endpoint():
    assert _day_for("daily_sleep", {"id": "x", "day": "2024-06-01"}) == "2024-06-01"


def test_day_for_enhanced_tag_uses_start_day():
    record = {"id": "t1", "start_day": "2024-06-15", "end_day": "2024-06-15"}
    assert _day_for("enhanced_tag", record) == "2024-06-15"


def test_day_for_enhanced_tag_fallback_to_day():
    record = {"id": "t2", "day": "2024-06-20"}
    assert _day_for("enhanced_tag", record) == "2024-06-20"


def test_day_for_missing_day_returns_sentinel():
    assert _day_for("daily_sleep", {"id": "x"}) == "1970-01-01"


# ── _insert_records ───────────────────────────────────────────────────────────

def test_insert_records_writes_rows(conn):
    records = [
        {"id": "s1", "day": "2024-01-01", "score": 82},
        {"id": "s2", "day": "2024-01-02", "score": 77},
    ]
    n = _insert_records(conn, "raw_daily_sleep", "kartik", "daily_sleep", records, FETCHED)
    assert n == 2
    rows = conn.execute("SELECT person_id, natural_key, day FROM raw_daily_sleep ORDER BY natural_key").fetchall()
    assert rows == [("kartik", "s1", date(2024, 1, 1)), ("kartik", "s2", date(2024, 1, 2))]


def test_insert_records_payload_is_json(conn):
    records = [{"id": "r1", "day": "2024-01-01", "score": 75}]
    _insert_records(conn, "raw_daily_readiness", "kartik", "daily_readiness", records, FETCHED)
    payload_str = conn.execute("SELECT payload FROM raw_daily_readiness").fetchone()[0]
    payload = json.loads(payload_str)
    assert payload["score"] == 75


def test_insert_records_empty_list_returns_zero(conn):
    n = _insert_records(conn, "raw_daily_sleep", "kartik", "daily_sleep", [], FETCHED)
    assert n == 0
    assert conn.execute("SELECT COUNT(*) FROM raw_daily_sleep").fetchone()[0] == 0


def test_insert_records_conflict_is_ignored(conn):
    records = [{"id": "dup", "day": "2024-01-01"}]
    _insert_records(conn, "raw_daily_sleep", "kartik", "daily_sleep", records, FETCHED)
    _insert_records(conn, "raw_daily_sleep", "kartik", "daily_sleep", records, FETCHED)
    count = conn.execute("SELECT COUNT(*) FROM raw_daily_sleep").fetchone()[0]
    assert count == 1


def test_insert_records_enhanced_tag_uses_start_day(conn):
    records = [{"id": "et1", "start_day": "2024-03-10", "tag_type_code": "tag_generic_tag"}]
    _insert_records(conn, "raw_enhanced_tag", "kartik", "enhanced_tag", records, FETCHED)
    row = conn.execute("SELECT day FROM raw_enhanced_tag").fetchone()
    assert row[0] == date(2024, 3, 10)


# ── backfill_person ───────────────────────────────────────────────────────────

def _make_client_mock(
    date_records: dict[str, list[dict]],
    hr_records: list[dict],
    pi_record: dict,
) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)

    def fake_fetch(endpoint, start, end, **kwargs):
        return date_records.get(endpoint, [])

    mock.fetch.side_effect = fake_fetch
    mock.fetch_heartrate.return_value = hr_records
    mock.get_one.return_value = pi_record
    return mock


@patch("scripts.backfill.OuraClient")
def test_backfill_person_writes_all_endpoints(mock_cls, conn):
    mock_client = _make_client_mock(
        date_records={
            "daily_sleep": [{"id": "s1", "day": "2024-01-01", "score": 80}],
            "daily_readiness": [{"id": "r1", "day": "2024-01-01", "score": 75}],
            "daily_activity": [{"id": "a1", "day": "2024-01-01"}],
            "daily_stress": [],
            "daily_spo2": [],
            "sleep_time": [],
            "sleep": [],
            "workout": [],
            "session": [],
            "enhanced_tag": [],
        },
        hr_records=[{"bpm": 62, "source": "awake", "timestamp": "2024-01-01T08:00:00+00:00"}],
        pi_record={"id": "pi1", "age": 30, "email": "a@b.com"},
    )
    mock_cls.return_value = mock_client

    backfill_person("kartik", "tok", conn, date(2024, 1, 1), date(2024, 1, 1), FETCHED)

    assert conn.execute("SELECT COUNT(*) FROM raw_daily_sleep").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM raw_daily_readiness").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM raw_heartrate").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM raw_personal_info").fetchone()[0] == 1


@patch("scripts.backfill.OuraClient")
def test_backfill_person_heartrate_natural_key_is_timestamp(mock_cls, conn):
    ts = "2024-01-01T08:00:00+00:00"
    mock_client = _make_client_mock(
        date_records={ep: [] for ep, _ in [("daily_sleep", "x"), ("daily_readiness", "x"),
                                            ("daily_activity", "x"), ("daily_stress", "x"),
                                            ("daily_spo2", "x"), ("sleep_time", "x"),
                                            ("sleep", "x"), ("workout", "x"), ("session", "x"),
                                            ("enhanced_tag", "x")]},
        hr_records=[{"bpm": 55, "source": "sleep", "timestamp": ts}],
        pi_record={"id": "pi1"},
    )
    mock_cls.return_value = mock_client

    backfill_person("kartik", "tok", conn, date(2024, 1, 1), date(2024, 1, 1), FETCHED)

    row = conn.execute("SELECT natural_key, day FROM raw_heartrate").fetchone()
    assert row[0] == ts
    assert row[1] == date(2024, 1, 1)


@patch("scripts.backfill.OuraClient")
def test_backfill_person_personal_info_constant_key(mock_cls, conn):
    mock_client = _make_client_mock(
        date_records={ep: [] for ep, _ in [("daily_sleep", "x"), ("daily_readiness", "x"),
                                            ("daily_activity", "x"), ("daily_stress", "x"),
                                            ("daily_spo2", "x"), ("sleep_time", "x"),
                                            ("sleep", "x"), ("workout", "x"), ("session", "x"),
                                            ("enhanced_tag", "x")]},
        hr_records=[],
        pi_record={"id": "pi1", "email": "user@example.com"},
    )
    mock_cls.return_value = mock_client

    backfill_person("kartik", "tok", conn, date(2024, 1, 1), date(2024, 1, 1), FETCHED)

    row = conn.execute("SELECT natural_key FROM raw_personal_info").fetchone()
    assert row[0] == "personal_info"


@patch("scripts.backfill.OuraClient")
def test_backfill_person_multiple_people_isolated(mock_cls, conn):
    def make_mock(person: str):
        return _make_client_mock(
            date_records={"daily_sleep": [{"id": f"s_{person}", "day": "2024-01-01"}],
                          **{ep: [] for ep in ["daily_readiness", "daily_activity", "daily_stress",
                                               "daily_spo2", "sleep_time", "sleep", "workout",
                                               "session", "enhanced_tag"]}},
            hr_records=[],
            pi_record={"id": f"pi_{person}"},
        )

    mock_cls.side_effect = [make_mock("kartik"), make_mock("partner")]

    for person in ("kartik", "partner"):
        backfill_person(person, "tok", conn, date(2024, 1, 1), date(2024, 1, 1), FETCHED)

    persons = {r[0] for r in conn.execute("SELECT person_id FROM raw_daily_sleep").fetchall()}
    assert persons == {"kartik", "partner"}


# ── main (CLI) ────────────────────────────────────────────────────────────────

@patch("scripts.backfill.settings")
@patch("scripts.backfill.backfill_person")
@patch("scripts.backfill.dbmod")
def test_main_calls_backfill_for_each_person(mock_db, mock_backfill_person, mock_settings):
    mock_settings.tokens.return_value = {"kartik": "tok_k", "partner": "tok_p"}
    mock_db.connect.return_value = MagicMock()
    mock_db.get_db_path.return_value = "test.duckdb"

    main(["--start", "2024-01-01"])

    assert mock_backfill_person.call_count == 2
    persons_called = {call.args[0] for call in mock_backfill_person.call_args_list}
    assert persons_called == {"kartik", "partner"}


@patch("scripts.backfill.settings")
def test_main_exits_when_no_tokens(mock_settings):
    mock_settings.tokens.return_value = {}
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 1
