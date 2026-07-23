"""Schema creation for the agent memory database.

Run this module directly (``python -m database.memory.init_memory_db``)
to (re)create ``agent_memory.db`` with an empty schema. Safe to re-run:
every statement uses ``CREATE TABLE IF NOT EXISTS``.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH: Path = Path(__file__).resolve().parent / "agent_memory.db"

_SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        started_at TEXT,
        ended_at   TEXT,
        user_id    TEXT,
        status     TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS messages (
        message_id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        sender     TEXT,
        message    TEXT,
        timestamp  TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_outputs (
        output_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        agent_name TEXT,
        output     TEXT,
        timestamp  TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tool_calls (
        tool_call_id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id   TEXT,
        tool_name    TEXT,
        arguments    TEXT,
        result       TEXT,
        timestamp    TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS execution_logs (
        log_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        log_entry  TEXT,
        timestamp  TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages (session_id)",
    "CREATE INDEX IF NOT EXISTS idx_agent_outputs_session ON agent_outputs (session_id)",
    "CREATE INDEX IF NOT EXISTS idx_tool_calls_session ON tool_calls (session_id)",
    "CREATE INDEX IF NOT EXISTS idx_execution_logs_session ON execution_logs (session_id)",
)


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open a connection to the memory database with sane defaults."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_memory_db(db_path: Path = DB_PATH) -> None:
    """Create every table (and index) in the memory schema if missing."""
    with get_connection(db_path) as conn:
        for statement in _SCHEMA_STATEMENTS:
            conn.execute(statement)
        conn.commit()


if __name__ == "__main__":
    init_memory_db()
    print(f"memory database initialised at {DB_PATH}")
