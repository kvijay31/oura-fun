"""DuckDB connection and raw schema management for oura-fun."""

from __future__ import annotations

import os
from pathlib import Path

import duckdb

_DB_ENV_VAR = "OURA_DB_PATH"
_DEFAULT_DB_PATH = "oura.duckdb"

# One table per Oura API endpoint.  Schema: (person_id, natural_key, day, payload, fetched_at).
# natural_key is the Oura record 'id' for most endpoints; for heartrate it is the
# ISO-8601 timestamp; for personal_info callers use "personal_info" as a constant.
# day is the calendar date the record belongs to (date portion of timestamp for heartrate).
# Every fetch is kept; views dedupe to latest fetched_at per (person_id, natural_key).
ENDPOINT_TABLES: list[str] = [
    "raw_daily_sleep",
    "raw_sleep",
    "raw_daily_readiness",
    "raw_daily_activity",
    "raw_daily_stress",
    "raw_daily_spo2",
    "raw_heartrate",
    "raw_workout",
    "raw_session",
    "raw_enhanced_tag",
    "raw_sleep_time",
    "raw_personal_info",
]

_CREATE_TABLE_SQL = """\
CREATE TABLE IF NOT EXISTS {table} (
    person_id   TEXT      NOT NULL,
    natural_key TEXT      NOT NULL,
    day         DATE      NOT NULL,
    payload     JSON      NOT NULL,
    fetched_at  TIMESTAMP NOT NULL,
    PRIMARY KEY (person_id, natural_key, day, fetched_at)
)"""
# fetched_at is stored as UTC; callers must pass timezone-naive datetime objects in UTC
# (or use datetime.now(timezone.utc).replace(tzinfo=None) before inserting).


def get_db_path() -> Path:
    return Path(os.environ.get(_DB_ENV_VAR, _DEFAULT_DB_PATH))


def connect(db_path: Path | str | None = None) -> duckdb.DuckDBPyConnection:
    path = Path(db_path) if db_path is not None else get_db_path()
    return duckdb.connect(str(path))


_CREATE_PEOPLE_SQL = """\
CREATE TABLE IF NOT EXISTS people (
    person_id    TEXT      NOT NULL PRIMARY KEY,
    token        TEXT      NOT NULL,
    added_at     TIMESTAMP NOT NULL
)"""


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create all raw endpoint tables and the people registry if they don't already exist."""
    conn.execute(_CREATE_PEOPLE_SQL)
    for table in ENDPOINT_TABLES:
        conn.execute(_CREATE_TABLE_SQL.format(table=table))


def init_db(conn: duckdb.DuckDBPyConnection) -> None:
    """Create raw tables, people registry, and derived views (idempotent)."""
    from oura_fun.views import create_views
    init_schema(conn)
    create_views(conn)


def upsert_person(conn: duckdb.DuckDBPyConnection, person_id: str, token: str) -> None:
    """Insert or replace a person + token in the people registry."""
    from datetime import datetime, timezone
    added_at = datetime.now(timezone.utc).replace(tzinfo=None)
    conn.execute(
        "INSERT INTO people (person_id, token, added_at) VALUES (?, ?, ?)"
        " ON CONFLICT (person_id) DO UPDATE SET token = excluded.token, added_at = excluded.added_at",
        [person_id, token, added_at],
    )


def list_people_from_db(conn: duckdb.DuckDBPyConnection) -> dict[str, str]:
    """Return {person_id: token} for all entries in the people registry."""
    rows = conn.execute("SELECT person_id, token FROM people ORDER BY added_at").fetchall()
    return {r[0]: r[1] for r in rows}
