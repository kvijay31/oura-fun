"""Initialize or migrate the DuckDB schema for oura-fun.

Usage:
    uv run python scripts/init_schema.py [db_path]

If db_path is omitted the value of OURA_DB_PATH is used, falling back to oura.duckdb.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from oura_fun.db import ENDPOINT_TABLES, connect, get_db_path, init_schema


def main() -> None:
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else get_db_path()
    print(f"Initializing schema at: {db_path}")
    with connect(db_path) as conn:
        init_schema(conn)
    print(f"Done. {len(ENDPOINT_TABLES)} tables ready:")
    for table in ENDPOINT_TABLES:
        print(f"  {table}")


if __name__ == "__main__":
    main()
