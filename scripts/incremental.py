"""F2.4: Incremental script — re-pull last 14 days daily to catch Oura backfills/revisions.

Usage:
    uv run python scripts/incremental.py [--days N] [--db-path PATH]

Options:
    --days      How many trailing days to re-fetch (default: 14)
    --db-path   DuckDB file path (default: OURA_DB_PATH env var or oura.duckdb)

Reads OURA_TOKEN_<PERSON> from environment / .env and updates all persons.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from oura_fun import db as dbmod
from oura_fun.config import settings
from backfill import backfill_person

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=14, help="Trailing days to re-fetch (default: 14)")
    parser.add_argument("--db-path", default=None, help="DuckDB file path")
    args = parser.parse_args(argv)

    today = date.today()
    start = today - timedelta(days=args.days - 1)

    tokens = settings.tokens()
    if not tokens:
        log.error("No OURA_TOKEN_<PERSON> variables found in environment / .env. Aborting.")
        sys.exit(1)

    db_path = args.db_path if args.db_path else dbmod.get_db_path()
    conn = dbmod.connect(db_path)
    dbmod.init_schema(conn)
    fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)

    log.info(
        "Incremental run: window=%s → %s (%d days), persons=%s, db=%s",
        start, today, args.days, list(tokens), db_path,
    )

    for person_id, token in tokens.items():
        backfill_person(person_id, token, conn, start, today, fetched_at)

    conn.close()
    log.info("Done. %d person(s) updated.", len(tokens))


if __name__ == "__main__":
    main()
