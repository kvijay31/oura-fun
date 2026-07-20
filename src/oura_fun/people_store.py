"""Durable person/token storage backed by a local DuckDB file.

Stores people added via the UI in a separate gitignored DB so token
discovery survives server restarts without touching .env.
"""

from __future__ import annotations

import datetime
import os
from pathlib import Path

import duckdb

_PEOPLE_DB_ENV_VAR = "OURA_PEOPLE_DB_PATH"
_DEFAULT_PEOPLE_DB_PATH = "people.duckdb"

_CREATE_TABLE_SQL = """\
CREATE TABLE IF NOT EXISTS people (
    person_id TEXT      NOT NULL PRIMARY KEY,
    token     TEXT      NOT NULL,
    added_at  TIMESTAMP NOT NULL
)"""


def get_db_path() -> Path:
    return Path(os.environ.get(_PEOPLE_DB_ENV_VAR, _DEFAULT_PEOPLE_DB_PATH))


def _connect() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(get_db_path()))


def _ensure_table(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(_CREATE_TABLE_SQL)


def add_person(person_id: str, token: str) -> None:
    """Insert or replace a person's token. person_id is stored as lowercase."""
    pid = person_id.lower()
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    with _connect() as conn:
        _ensure_table(conn)
        conn.execute(
            "INSERT OR REPLACE INTO people (person_id, token, added_at) VALUES (?, ?, ?)",
            [pid, token, now],
        )


def remove_person(person_id: str) -> None:
    """Delete a person from the store."""
    with _connect() as conn:
        _ensure_table(conn)
        conn.execute("DELETE FROM people WHERE person_id = ?", [person_id.lower()])


def get_tokens() -> dict[str, str]:
    """Return {person_id: token} for all rows in the people table."""
    try:
        with _connect() as conn:
            _ensure_table(conn)
            rows = conn.execute("SELECT person_id, token FROM people").fetchall()
            return {row[0]: row[1] for row in rows}
    except Exception:
        return {}


def list_people_store() -> list[dict]:
    """Return all rows as dicts with person_id, token, added_at."""
    try:
        with _connect() as conn:
            _ensure_table(conn)
            rows = conn.execute(
                "SELECT person_id, token, added_at FROM people ORDER BY added_at"
            ).fetchall()
            return [
                {"person_id": r[0], "token": r[1], "added_at": r[2]} for r in rows
            ]
    except Exception:
        return []
