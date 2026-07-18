"""DuckDB lifecycle for the F9.2 API layer.

Startup: tries to connect and create views over the raw tables from F2.1.
Requests: each handler receives a short-lived connection via get_db().
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Generator

import duckdb
from fastapi import HTTPException

from .views import VIEW_SQLS

logger = logging.getLogger(__name__)

_db_path: Path | None = None


def get_db_path() -> Path:
    return Path(os.environ.get("OURA_DB_PATH", "oura.duckdb"))


def init_db() -> tuple[bool, str]:
    """Try to connect and materialise views. Returns (ready, reason)."""
    global _db_path
    path = get_db_path()
    if not path.exists():
        return False, f"DB file not found at {path} — run ingestion first"
    try:
        conn = duckdb.connect(str(path))
        for sql in VIEW_SQLS:
            conn.execute(sql)
        conn.close()
        _db_path = path
        logger.info("DuckDB ready at %s", path)
        return True, "ok"
    except Exception as exc:
        logger.warning("DuckDB init failed: %s", exc)
        return False, str(exc)


def get_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """FastAPI dependency: per-request DuckDB connection."""
    if _db_path is None:
        raise HTTPException(
            status_code=503,
            detail="Database not ready — run ingestion pipeline first (see scripts/backfill.py)",
        )
    conn = duckdb.connect(str(_db_path))
    try:
        yield conn
    finally:
        conn.close()
