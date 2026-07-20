"""F2.6: Sanity-check script — validate ingested Oura data after backfill/incremental.

Usage:
    uv run python scripts/sanity_check.py [--db-path PATH]

Options:
    --db-path   DuckDB file path (default: OURA_DB_PATH env var or oura.duckdb)

Exits 0 when all checks pass, 1 when any issue is found.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from oura_fun import db as dbmod
from oura_fun.sanity import run_checks
from oura_fun.views import create_views

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", default=None, help="DuckDB file path")
    args = parser.parse_args(argv)

    db_path = args.db_path if args.db_path else dbmod.get_db_path()
    conn = dbmod.connect(db_path)
    dbmod.init_schema(conn)
    create_views(conn)

    log.info("Running sanity checks on %s", db_path)
    result = run_checks(conn)
    conn.close()

    if result.ok:
        log.info("All sanity checks passed.")
    else:
        total_gaps = sum(
            len(dates)
            for tables in result.date_gaps.values()
            for dates in tables.values()
        )
        total_bad = sum(len(rows) for rows in result.bad_sleep_durations.values())
        log.error(
            "Sanity checks FAILED: %d date gap(s), %d impossible sleep duration(s).",
            total_gaps,
            total_bad,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
