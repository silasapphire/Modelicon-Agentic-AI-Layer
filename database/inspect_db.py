"""Ad-hoc CLI for peeking into either database without installing sqlite3.

Usage:
    python -m database.inspect_db building
    python -m database.inspect_db memory
    python -m database.inspect_db building --table hvac_readings --limit 20
    python -m database.inspect_db memory --table sessions
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from database.building.init_building_db import DB_PATH as BUILDING_DB_PATH
from database.memory.init_memory_db import DB_PATH as MEMORY_DB_PATH

_DB_PATHS = {"building": BUILDING_DB_PATH, "memory": MEMORY_DB_PATH}


def _list_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [r[0] for r in rows if r[0] != "sqlite_sequence"]


def inspect(db_path: Path, table: str | None, limit: int) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    tables = [table] if table else _list_tables(conn)

    print(f"=== {db_path} ===")
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"\n-- {t} ({count} row(s), showing up to {limit}) --")
        for row in conn.execute(f"SELECT * FROM {t} LIMIT {limit}"):
            print(dict(row))
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", choices=sorted(_DB_PATHS), help="which database to inspect")
    parser.add_argument("--table", default=None, help="limit to one table (default: all tables)")
    parser.add_argument("--limit", type=int, default=10, help="max rows per table (default: 10)")
    args = parser.parse_args()

    inspect(_DB_PATHS[args.database], args.table, args.limit)
