"""F2.3: Backfill script — pull full history per configured token, write raw rows.

Usage:
    uv run python scripts/backfill.py [--start YYYY-MM-DD] [--db-path PATH]

Options:
    --start     Earliest date to fetch (default: 2020-01-01)
    --db-path   DuckDB file path (default: OURA_DB_PATH env var or oura.duckdb)

Reads OURA_TOKEN_<PERSON> from environment / .env and backfills all persons.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from oura_fun import db as dbmod
from oura_fun.client import OuraClient
from oura_fun.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

_DEFAULT_START = date(2020, 1, 1)

# Endpoints using start_date/end_date params and their raw table names.
_DATE_ENDPOINTS: list[tuple[str, str]] = [
    ("daily_sleep",     "raw_daily_sleep"),
    ("daily_readiness", "raw_daily_readiness"),
    ("daily_activity",  "raw_daily_activity"),
    ("daily_stress",    "raw_daily_stress"),
    ("daily_spo2",      "raw_daily_spo2"),
    ("sleep_time",      "raw_sleep_time"),
    ("sleep",           "raw_sleep"),
    ("workout",         "raw_workout"),
    ("session",         "raw_session"),
    ("enhanced_tag",    "raw_enhanced_tag"),
]


def _day_for(endpoint: str, record: dict[str, Any]) -> str:
    """Extract the calendar date a record belongs to."""
    if endpoint == "enhanced_tag":
        # enhanced_tag has start_day instead of day
        return record.get("start_day") or record.get("day", "1970-01-01")
    return record.get("day", "1970-01-01")


def _insert_records(
    conn: Any,
    table: str,
    person_id: str,
    endpoint: str,
    records: list[dict[str, Any]],
    fetched_at: datetime,
) -> int:
    if not records:
        return 0
    rows = [
        (
            person_id,
            r["id"],
            _day_for(endpoint, r),
            json.dumps(r),
            fetched_at,
        )
        for r in records
    ]
    conn.executemany(
        f"INSERT INTO {table} (person_id, natural_key, day, payload, fetched_at) "
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
        rows,
    )
    return len(rows)


def backfill_person(
    person_id: str,
    token: str,
    conn: Any,
    start: date,
    today: date,
    fetched_at: datetime,
) -> None:
    log.info("Backfilling person: %s  (%s → %s)", person_id, start, today)
    with OuraClient(token) as client:
        # date-range endpoints
        for endpoint, table in _DATE_ENDPOINTS:
            records = client.fetch(endpoint, start, today)
            n = _insert_records(conn, table, person_id, endpoint, records, fetched_at)
            log.info("  %-22s %d rows", endpoint, n)

        # heartrate uses start_datetime/end_datetime, timestamp is the natural key
        start_dt = f"{start}T00:00:00"
        end_dt = f"{today}T23:59:59"
        hr_records = client.fetch_heartrate(start_dt, end_dt)
        if hr_records:
            hr_rows = [
                (
                    person_id,
                    r["timestamp"],
                    r["timestamp"][:10],
                    json.dumps(r),
                    fetched_at,
                )
                for r in hr_records
            ]
            conn.executemany(
                "INSERT INTO raw_heartrate (person_id, natural_key, day, payload, fetched_at) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                hr_rows,
            )
        log.info("  %-22s %d rows", "heartrate", len(hr_records))

        # personal_info is a single-record endpoint; natural_key is a constant
        pi = client.get_one("personal_info")
        conn.execute(
            "INSERT INTO raw_personal_info (person_id, natural_key, day, payload, fetched_at) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
            [person_id, "personal_info", str(today), json.dumps(pi), fetched_at],
        )
        log.info("  %-22s 1 row", "personal_info")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default=str(_DEFAULT_START), help="Earliest fetch date (YYYY-MM-DD)")
    parser.add_argument("--db-path", default=None, help="DuckDB file path")
    args = parser.parse_args(argv)

    start = date.fromisoformat(args.start)
    today = date.today()

    tokens = settings.tokens()
    if not tokens:
        log.error("No OURA_TOKEN_<PERSON> variables found in environment / .env. Aborting.")
        sys.exit(1)

    db_path = args.db_path if args.db_path else dbmod.get_db_path()
    conn = dbmod.connect(db_path)
    dbmod.init_schema(conn)
    fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)

    log.info("Backfill run: start=%s end=%s persons=%s db=%s", start, today, list(tokens), db_path)
    for person_id, token in tokens.items():
        backfill_person(person_id, token, conn, start, today, fetched_at)

    conn.close()
    log.info("Done. All %d person(s) backfilled.", len(tokens))


if __name__ == "__main__":
    main()
