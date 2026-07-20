"""F10.1: On-demand refresh — background task state and runner.

Exposes start_refresh() and get_status() for use by the API routes.
All DuckDB write operations are serialised through a single-worker executor
so concurrent refresh requests never open two write connections simultaneously.
"""

from __future__ import annotations

import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Import backfill_person from scripts/ without making it a package dependency.
_scripts_dir = str(Path(__file__).resolve().parents[3] / "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)
from backfill import backfill_person  # type: ignore[import]

from oura_fun import db as dbmod
from oura_fun.config import settings

_THROTTLE_SECS = 300  # skip if last refresh was < 5 min ago
_REFRESH_DAYS = 2

# All refresh jobs run sequentially through this executor to avoid
# concurrent write connections to DuckDB.
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="oura-refresh")
_state_lock = threading.Lock()
# {person_id: {running, last_refresh, error}}
_state: dict[str, dict[str, Any]] = {}


def _is_throttled(person_id: str) -> tuple[bool, str]:
    with _state_lock:
        s = _state.get(person_id, {})
    if s.get("running"):
        return True, "already_running"
    lr: datetime | None = s.get("last_refresh")
    if lr is not None:
        elapsed = (datetime.now(timezone.utc) - lr).total_seconds()
        if elapsed < _THROTTLE_SECS:
            remaining = int(_THROTTLE_SECS - elapsed)
            return True, f"throttled (retry in {remaining}s)"
    return False, ""


def _do_refresh(person_tokens: dict[str, str]) -> None:
    today = date.today()
    start = today - timedelta(days=_REFRESH_DAYS - 1)
    fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        conn = dbmod.connect(dbmod.get_db_path())
        dbmod.init_schema(conn)
        try:
            for person_id, token in person_tokens.items():
                backfill_person(person_id, token, conn, start, today, fetched_at)
                with _state_lock:
                    _state[person_id] = {
                        "running": False,
                        "last_refresh": datetime.now(timezone.utc),
                        "error": None,
                    }
        finally:
            conn.close()
    except Exception as exc:
        for person_id in person_tokens:
            with _state_lock:
                prev = _state.get(person_id, {})
                _state[person_id] = {
                    "running": False,
                    "last_refresh": prev.get("last_refresh"),
                    "error": str(exc),
                }


def start_refresh(person_id: str | None = None) -> dict[str, str]:
    """Enqueue a background refresh; returns {person_id: status_string}."""
    tokens = settings.tokens()
    if not tokens:
        return {}

    if person_id is not None:
        if person_id not in tokens:
            return {person_id: "no_token"}
        candidates = {person_id: tokens[person_id]}
    else:
        candidates = dict(tokens)

    result: dict[str, str] = {}
    to_run: dict[str, str] = {}

    for pid, token in candidates.items():
        throttled, reason = _is_throttled(pid)
        if throttled:
            result[pid] = reason
        else:
            to_run[pid] = token
            result[pid] = "started"

    if to_run:
        with _state_lock:
            for pid in to_run:
                prev = _state.get(pid, {})
                _state[pid] = {
                    "running": True,
                    "last_refresh": prev.get("last_refresh"),
                    "error": None,
                }
        _executor.submit(_do_refresh, to_run)

    return result


def get_status() -> dict[str, dict[str, Any]]:
    """Return current refresh state for all known people."""
    with _state_lock:
        return {
            pid: {
                "running": s["running"],
                "last_refresh": s["last_refresh"].isoformat() if s.get("last_refresh") else None,
                "error": s.get("error"),
            }
            for pid, s in _state.items()
        }


def any_running() -> bool:
    """True if any person's refresh is currently in progress."""
    with _state_lock:
        return any(s.get("running", False) for s in _state.values())
