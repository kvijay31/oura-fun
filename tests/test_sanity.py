"""Tests for F2.6: sanity checks."""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from oura_fun.db import init_schema
from oura_fun.sanity import (
    SanityResult,
    check_date_gaps,
    check_sleep_durations,
    row_counts,
    run_checks,
)
from oura_fun.views import create_views


@pytest.fixture()
def conn():
    c = duckdb.connect(":memory:")
    init_schema(c)
    create_views(c)
    yield c
    c.close()


FETCHED = datetime(2025, 1, 15, 12, 0, 0)


def _insert_daily_sleep(conn, person_id: str, days: list[str]) -> None:
    for d in days:
        conn.execute(
            "INSERT INTO raw_daily_sleep (person_id, natural_key, day, payload, fetched_at) "
            "VALUES (?, ?, ?, ?, ?)",
            [person_id, f"s_{d}", d, json.dumps({"id": f"s_{d}", "day": d, "score": 80}), FETCHED],
        )


def _insert_sleep_period(conn, person_id: str, natural_key: str, day: str, duration_s: int) -> None:
    payload = {
        "id": natural_key,
        "day": day,
        "bedtime_start": f"{day}T22:00:00+00:00",
        "bedtime_end": f"{day}T06:00:00+00:00",
        "total_sleep_duration": duration_s,
        "type": "long_sleep",
    }
    conn.execute(
        "INSERT INTO raw_sleep (person_id, natural_key, day, payload, fetched_at) "
        "VALUES (?, ?, ?, ?, ?)",
        [person_id, natural_key, day, json.dumps(payload), FETCHED],
    )


# ── row_counts ────────────────────────────────────────────────────────────────

def test_row_counts_empty(conn):
    counts = row_counts(conn)
    assert all(v == 0 for v in counts.values())
    assert "raw_daily_sleep" in counts


def test_row_counts_with_data(conn):
    _insert_daily_sleep(conn, "kartik", ["2024-01-01", "2024-01-02"])
    counts = row_counts(conn)
    assert counts["raw_daily_sleep"] == 2
    assert counts["raw_daily_readiness"] == 0


# ── check_date_gaps ───────────────────────────────────────────────────────────

def test_no_gaps_contiguous(conn):
    _insert_daily_sleep(conn, "kartik", ["2024-01-01", "2024-01-02", "2024-01-03"])
    gaps = check_date_gaps(conn, "kartik", "raw_daily_sleep")
    assert gaps == []


def test_single_row_no_gaps(conn):
    _insert_daily_sleep(conn, "kartik", ["2024-06-15"])
    gaps = check_date_gaps(conn, "kartik", "raw_daily_sleep")
    assert gaps == []


def test_two_rows_no_gap(conn):
    _insert_daily_sleep(conn, "kartik", ["2024-01-01", "2024-01-02"])
    gaps = check_date_gaps(conn, "kartik", "raw_daily_sleep")
    assert gaps == []


def test_detects_single_gap(conn):
    _insert_daily_sleep(conn, "kartik", ["2024-01-01", "2024-01-03"])
    gaps = check_date_gaps(conn, "kartik", "raw_daily_sleep")
    assert gaps == [date(2024, 1, 2)]


def test_detects_multiple_gaps(conn):
    _insert_daily_sleep(conn, "kartik", ["2024-01-01", "2024-01-04", "2024-01-07"])
    gaps = check_date_gaps(conn, "kartik", "raw_daily_sleep")
    assert date(2024, 1, 2) in gaps
    assert date(2024, 1, 3) in gaps
    assert date(2024, 1, 5) in gaps
    assert date(2024, 1, 6) in gaps
    assert len(gaps) == 4


def test_empty_table_no_gaps(conn):
    gaps = check_date_gaps(conn, "kartik", "raw_daily_sleep")
    assert gaps == []


def test_gaps_isolated_per_person(conn):
    _insert_daily_sleep(conn, "kartik", ["2024-01-01", "2024-01-03"])
    _insert_daily_sleep(conn, "partner", ["2024-01-01", "2024-01-02", "2024-01-03"])
    kartik_gaps = check_date_gaps(conn, "kartik", "raw_daily_sleep")
    partner_gaps = check_date_gaps(conn, "partner", "raw_daily_sleep")
    assert kartik_gaps == [date(2024, 1, 2)]
    assert partner_gaps == []


# ── check_sleep_durations ─────────────────────────────────────────────────────

def test_normal_sleep_duration_passes(conn):
    _insert_sleep_period(conn, "kartik", "sp1", "2024-01-01", 25_200)  # 7 h
    bad = check_sleep_durations(conn, "kartik")
    assert bad == []


def test_sleep_duration_exactly_at_limit_passes(conn):
    _insert_sleep_period(conn, "kartik", "sp1", "2024-01-01", 86_400)  # exactly 24 h
    bad = check_sleep_durations(conn, "kartik")
    assert bad == []


def test_sleep_duration_over_limit_flagged(conn):
    _insert_sleep_period(conn, "kartik", "sp1", "2024-01-01", 86_401)
    bad = check_sleep_durations(conn, "kartik")
    assert len(bad) == 1
    assert bad[0]["natural_key"] == "sp1"
    assert bad[0]["total_sleep_duration"] == 86_401


def test_negative_sleep_duration_flagged(conn):
    _insert_sleep_period(conn, "kartik", "sp1", "2024-01-01", -1)
    bad = check_sleep_durations(conn, "kartik")
    assert len(bad) == 1
    assert bad[0]["total_sleep_duration"] == -1


def test_null_sleep_duration_ignored(conn):
    payload = {"id": "sp_null", "day": "2024-01-01", "type": "long_sleep"}
    conn.execute(
        "INSERT INTO raw_sleep (person_id, natural_key, day, payload, fetched_at) "
        "VALUES (?, ?, ?, ?, ?)",
        ["kartik", "sp_null", "2024-01-01", json.dumps(payload), FETCHED],
    )
    bad = check_sleep_durations(conn, "kartik")
    assert bad == []


def test_multiple_bad_durations_all_returned(conn):
    _insert_sleep_period(conn, "kartik", "sp1", "2024-01-01", 90_000)
    _insert_sleep_period(conn, "kartik", "sp2", "2024-01-02", 100_000)
    bad = check_sleep_durations(conn, "kartik")
    assert len(bad) == 2


# ── run_checks ────────────────────────────────────────────────────────────────

def test_run_checks_empty_db_ok(conn):
    result = run_checks(conn)
    assert result.ok
    assert all(v == 0 for v in result.row_counts.values())


def test_run_checks_clean_data_ok(conn):
    _insert_daily_sleep(conn, "kartik", ["2024-01-01", "2024-01-02", "2024-01-03"])
    _insert_sleep_period(conn, "kartik", "sp1", "2024-01-01", 28_800)
    result = run_checks(conn)
    assert result.ok
    assert result.row_counts["raw_daily_sleep"] == 3


def test_run_checks_detects_date_gap(conn):
    _insert_daily_sleep(conn, "kartik", ["2024-01-01", "2024-01-03"])
    result = run_checks(conn)
    assert not result.ok
    assert "kartik" in result.date_gaps
    assert date(2024, 1, 2) in result.date_gaps["kartik"]["raw_daily_sleep"]


def test_run_checks_detects_bad_sleep_duration(conn):
    _insert_daily_sleep(conn, "kartik", ["2024-01-01"])
    _insert_sleep_period(conn, "kartik", "sp1", "2024-01-01", 99_999)
    result = run_checks(conn)
    assert not result.ok
    assert "kartik" in result.bad_sleep_durations
    assert result.bad_sleep_durations["kartik"][0]["total_sleep_duration"] == 99_999


def test_sanity_result_ok_property():
    r = SanityResult()
    assert r.ok

    r.date_gaps["person"] = {"table": [date(2024, 1, 1)]}
    assert not r.ok


# ── CLI (sanity_check script) ─────────────────────────────────────────────────

def test_sanity_check_main_exits_0_on_clean_db(tmp_path):
    import duckdb as _duckdb
    from oura_fun.db import init_schema as _init, connect as _connect
    from oura_fun.views import create_views as _views

    db = str(tmp_path / "test.duckdb")
    c = _connect(db)
    _init(c)
    _views(c)
    _insert_daily_sleep(c, "kartik", ["2024-01-01", "2024-01-02"])
    c.close()

    from sanity_check import main
    main(["--db-path", db])  # should not raise


def test_sanity_check_main_exits_1_on_bad_data(tmp_path):
    import duckdb as _duckdb
    from oura_fun.db import init_schema as _init, connect as _connect
    from oura_fun.views import create_views as _views

    db = str(tmp_path / "test.duckdb")
    c = _connect(db)
    _init(c)
    _views(c)
    _insert_daily_sleep(c, "kartik", ["2024-01-01", "2024-01-03"])  # gap on Jan 2
    c.close()

    from sanity_check import main
    with pytest.raises(SystemExit) as exc_info:
        main(["--db-path", db])
    assert exc_info.value.code == 1
