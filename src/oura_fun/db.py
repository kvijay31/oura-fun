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


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create all raw endpoint tables if they don't already exist."""
    for table in ENDPOINT_TABLES:
        conn.execute(_CREATE_TABLE_SQL.format(table=table))


def init_db(conn: duckdb.DuckDBPyConnection) -> None:
    """Create raw tables and derived views (idempotent)."""
    from oura_fun.views import create_views
    init_schema(conn)
    create_views(conn)
