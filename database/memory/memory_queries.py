"""Read/write helpers for the agent memory database.

Every write helper opens its own short-lived connection (context manager,
commits on exit) and every read helper returns plain dictionaries, never
raw ``sqlite3.Row`` / tuple objects — consistent with
``database.building.building_queries``.

``arguments`` / ``result`` / ``output`` values that aren't already
strings are JSON-serialised before being stored, and JSON-decoded again
on the way out where that round-trip is unambiguous (tool_calls).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from database.memory.init_memory_db import DB_PATH, get_connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value)
    except TypeError:
        return str(value)


def _maybe_json(value: Optional[str]) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


# --------------------------------------------------------------------------
# Sessions
# --------------------------------------------------------------------------

def create_session(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> str:
    """Start a new session and return its ``session_id``.

    Generates a UUID4 session id when none is supplied.
    """
    session_id = session_id or str(uuid.uuid4())
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO sessions (session_id, started_at, ended_at, user_id, status) "
            "VALUES (?, ?, NULL, ?, ?)",
            (session_id, _now(), user_id, "active"),
        )
        conn.commit()
    return session_id


def end_session(session_id: str, status: str = "completed", db_path: Path = DB_PATH) -> None:
    """Mark a session as finished, recording an end timestamp."""
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE sessions SET ended_at = ?, status = ? WHERE session_id = ?",
            (_now(), status, session_id),
        )
        conn.commit()


# --------------------------------------------------------------------------
# Writes
# --------------------------------------------------------------------------

def save_message(session_id: str, sender: str, message: str, db_path: Path = DB_PATH) -> int:
    """Persist one conversation message and return its ``message_id``."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO messages (session_id, sender, message, timestamp) VALUES (?, ?, ?, ?)",
            (session_id, sender, message, _now()),
        )
        conn.commit()
        return cursor.lastrowid


def save_agent_output(session_id: str, agent_name: str, output: Any, db_path: Path = DB_PATH) -> int:
    """Persist one agent's output and return its ``output_id``."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO agent_outputs (session_id, agent_name, output, timestamp) VALUES (?, ?, ?, ?)",
            (session_id, agent_name, _to_text(output), _now()),
        )
        conn.commit()
        return cursor.lastrowid


def save_tool_call(
    session_id: str,
    tool_name: str,
    arguments: Any,
    result: Any,
    db_path: Path = DB_PATH,
) -> int:
    """Persist one MCP tool invocation and return its ``tool_call_id``."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO tool_calls (session_id, tool_name, arguments, result, timestamp) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, tool_name, _to_text(arguments), _to_text(result), _now()),
        )
        conn.commit()
        return cursor.lastrowid


def save_log(session_id: str, log_entry: str, db_path: Path = DB_PATH) -> int:
    """Persist one execution log line and return its ``log_id``."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO execution_logs (session_id, log_entry, timestamp) VALUES (?, ?, ?)",
            (session_id, log_entry, _now()),
        )
        conn.commit()
        return cursor.lastrowid


# --------------------------------------------------------------------------
# Reads
# --------------------------------------------------------------------------

def get_conversation(session_id: str, db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    """Return every message in a session, oldest first."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY message_id ASC",
            (session_id,),
        ).fetchall()
    return _rows_to_dicts(rows)


def get_session_history(session_id: str, db_path: Path = DB_PATH) -> dict[str, Any]:
    """Return everything recorded for a session: metadata plus every table.

    Shape::

        {
            "session": {...} | None,
            "messages": [...],
            "agent_outputs": [...],
            "tool_calls": [...],
            "execution_logs": [...],
        }
    """
    with get_connection(db_path) as conn:
        session_row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        messages = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY message_id ASC", (session_id,)
        ).fetchall()
        agent_outputs = conn.execute(
            "SELECT * FROM agent_outputs WHERE session_id = ? ORDER BY output_id ASC", (session_id,)
        ).fetchall()
        tool_calls = conn.execute(
            "SELECT * FROM tool_calls WHERE session_id = ? ORDER BY tool_call_id ASC", (session_id,)
        ).fetchall()
        execution_logs = conn.execute(
            "SELECT * FROM execution_logs WHERE session_id = ? ORDER BY log_id ASC", (session_id,)
        ).fetchall()

    tool_call_dicts = _rows_to_dicts(tool_calls)
    for entry in tool_call_dicts:
        entry["arguments"] = _maybe_json(entry.get("arguments"))
        entry["result"] = _maybe_json(entry.get("result"))

    return {
        "session": dict(session_row) if session_row is not None else None,
        "messages": _rows_to_dicts(messages),
        "agent_outputs": _rows_to_dicts(agent_outputs),
        "tool_calls": tool_call_dicts,
        "execution_logs": _rows_to_dicts(execution_logs),
    }


def list_sessions(db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    """Return every session, most recently started first."""
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM sessions ORDER BY started_at DESC").fetchall()
    return _rows_to_dicts(rows)
