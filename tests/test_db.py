"""Tests for DuckDB raw schema creation and insertion behaviour."""

from __future__ import annotations

import json
from datetime import datetime

import duckdb
import pytest

from oura_fun.db import ENDPOINT_TABLES, init_schema

# All fetched_at values are naive datetimes in UTC (TIMESTAMP column, no TZ info stored).


@pytest.fixture()
def conn():
    """In-memory DuckDB connection with schema initialised."""
    c = duckdb.connect(":memory:")
    init_schema(c)
    yield c
    c.close()


def test_all_tables_created(conn):
    existing = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
    assert set(ENDPOINT_TABLES) == existing


def test_insert_and_select_row(conn):
    fetched = datetime(2025, 1, 15, 12, 0, 0, tzinfo=None)
    payload = json.dumps({"id": "abc123", "day": "2025-01-15", "score": 82})
    conn.execute(
        "INSERT INTO raw_daily_sleep VALUES (?, ?, ?, ?, ?)",
        ["kartik", "abc123", "2025-01-15", payload, fetched],
    )
    rows = conn.execute("SELECT * FROM raw_daily_sleep").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "kartik"
    assert rows[0][1] == "abc123"


def test_multiple_fetches_same_natural_key_stored(conn):
    """Oura revises past days — two fetches of the same key must both be kept."""
    payload_v1 = json.dumps({"id": "rec1", "score": 80})
    payload_v2 = json.dumps({"id": "rec1", "score": 83})
    t1 = datetime(2025, 1, 15, 6, 0, 0, tzinfo=None)
    t2 = datetime(2025, 1, 16, 6, 0, 0, tzinfo=None)

    conn.execute(
        "INSERT INTO raw_daily_readiness VALUES (?, ?, ?, ?, ?)",
        ["kartik", "rec1", "2025-01-15", payload_v1, t1],
    )
    conn.execute(
        "INSERT INTO raw_daily_readiness VALUES (?, ?, ?, ?, ?)",
        ["kartik", "rec1", "2025-01-15", payload_v2, t2],
    )

    rows = conn.execute(
        "SELECT payload FROM raw_daily_readiness WHERE person_id='kartik' AND natural_key='rec1' ORDER BY fetched_at"
    ).fetchall()
    assert len(rows) == 2
    assert json.loads(rows[0][0])["score"] == 80
    assert json.loads(rows[1][0])["score"] == 83


def test_duplicate_primary_key_rejected(conn):
    """Inserting the same (person_id, natural_key, day, fetched_at) twice must fail."""
    fetched = datetime(2025, 1, 15, 12, 0, 0, tzinfo=None)
    payload = json.dumps({"id": "dup", "score": 75})
    conn.execute(
        "INSERT INTO raw_daily_sleep VALUES (?, ?, ?, ?, ?)",
        ["kartik", "dup", "2025-01-15", payload, fetched],
    )
    with pytest.raises(duckdb.ConstraintException):
        conn.execute(
            "INSERT INTO raw_daily_sleep VALUES (?, ?, ?, ?, ?)",
            ["kartik", "dup", "2025-01-15", payload, fetched],
        )


def test_multiple_people_isolated(conn):
    fetched = datetime(2025, 1, 15, 12, 0, 0, tzinfo=None)
    for person in ("kartik", "partner"):
        conn.execute(
            "INSERT INTO raw_daily_activity VALUES (?, ?, ?, ?, ?)",
            [person, "act1", "2025-01-15", json.dumps({"id": "act1", "person": person}), fetched],
        )
    rows = conn.execute(
        "SELECT person_id FROM raw_daily_activity ORDER BY person_id"
    ).fetchall()
    assert [r[0] for r in rows] == ["kartik", "partner"]


def test_heartrate_table_accepts_timestamp_natural_key(conn):
    fetched = datetime(2025, 1, 15, 12, 0, 0, tzinfo=None)
    conn.execute(
        "INSERT INTO raw_heartrate VALUES (?, ?, ?, ?, ?)",
        ["kartik", "2025-01-15T08:00:00+00:00", "2025-01-15", json.dumps({"bpm": 62, "source": "awake"}), fetched],
    )
    rows = conn.execute("SELECT * FROM raw_heartrate").fetchall()
    assert len(rows) == 1


def test_personal_info_table_accepts_constant_natural_key(conn):
    fetched = datetime(2025, 1, 15, 12, 0, 0, tzinfo=None)
    conn.execute(
        "INSERT INTO raw_personal_info VALUES (?, ?, ?, ?, ?)",
        ["kartik", "personal_info", "2025-01-15", json.dumps({"email": "k@example.com"}), fetched],
    )
    rows = conn.execute("SELECT * FROM raw_personal_info").fetchall()
    assert len(rows) == 1


def test_init_schema_is_idempotent(conn):
    """Calling init_schema a second time must not raise (IF NOT EXISTS)."""
    init_schema(conn)
    existing = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
    assert set(ENDPOINT_TABLES) == existing
