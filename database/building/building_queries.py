"""Reusable read queries over the building data database.

Every function here returns plain Python dictionaries (or lists / None),
never raw ``sqlite3.Row`` / tuple objects, so callers (MCP tools, the
Query Agent) can serialise results straight to JSON.

All timestamps are expected to be ISO-8601 strings (``YYYY-MM-DDTHH:MM:SS``,
optionally with an offset), which sort lexically the same as
chronologically — that lets "last N hours" queries use a simple string
comparison instead of relying on SQLite's date functions to understand a
particular timestamp dialect.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from database.building.init_building_db import DB_PATH, get_connection


def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[dict[str, Any]]:
    return dict(row) if row is not None else None


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def _cutoff_iso(hours: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


def get_latest_sensor_data(room_name: str | None = None, db_path: Path = DB_PATH) -> Optional[dict[str, Any]]:
    """Return the most recent HVAC reading, optionally scoped to a room."""
    query = """
        SELECT r.*, rm.room_name
        FROM hvac_readings r
        LEFT JOIN rooms rm ON rm.room_id = r.room_id
    """
    params: tuple[Any, ...] = ()
    if room_name:
        query += " WHERE rm.room_name = ?"
        params = (room_name,)
    query += " ORDER BY r.timestamp DESC LIMIT 1"

    with get_connection(db_path) as conn:
        row = conn.execute(query, params).fetchone()
    return _row_to_dict(row)


def get_room_temperature(room_name: str, db_path: Path = DB_PATH) -> Optional[dict[str, Any]]:
    """Return the latest temperature reading recorded for a named room."""
    query = """
        SELECT rm.room_name, r.temperature, r.supply_temp, r.return_temp, r.timestamp
        FROM hvac_readings r
        JOIN rooms rm ON rm.room_id = r.room_id
        WHERE rm.room_name = ?
        ORDER BY r.timestamp DESC
        LIMIT 1
    """
    with get_connection(db_path) as conn:
        row = conn.execute(query, (room_name,)).fetchone()
    return _row_to_dict(row)


def get_last_24h_average(room_name: str | None = None, db_path: Path = DB_PATH) -> dict[str, Any]:
    """Return average temperature/humidity/co2/power over the last 24 hours."""
    return get_average_over_hours(hours=24, room_name=room_name, db_path=db_path)


def get_average_over_hours(hours: int, room_name: str | None = None, db_path: Path = DB_PATH) -> dict[str, Any]:
    """Return averaged readings over an arbitrary rolling window."""
    query = """
        SELECT
            AVG(r.temperature) AS avg_temperature,
            AVG(r.humidity)    AS avg_humidity,
            AVG(r.co2)         AS avg_co2,
            AVG(r.power_kw)    AS avg_power_kw,
            COUNT(*)           AS sample_count
        FROM hvac_readings r
        LEFT JOIN rooms rm ON rm.room_id = r.room_id
        WHERE r.timestamp >= ?
    """
    params: list[Any] = [_cutoff_iso(hours)]
    if room_name:
        query += " AND rm.room_name = ?"
        params.append(room_name)

    with get_connection(db_path) as conn:
        row = conn.execute(query, params).fetchone()

    result = _row_to_dict(row) or {}
    result["window_hours"] = hours
    result["room_name"] = room_name
    return result


def get_energy_usage(room_name: str | None = None, hours: int = 24, db_path: Path = DB_PATH) -> dict[str, Any]:
    """Return summed energy usage (kWh) and average power draw (kW)."""
    query = """
        SELECT
            SUM(r.energy_kwh) AS total_energy_kwh,
            AVG(r.power_kw)   AS avg_power_kw,
            MAX(r.power_kw)   AS peak_power_kw,
            COUNT(*)          AS sample_count
        FROM hvac_readings r
        LEFT JOIN rooms rm ON rm.room_id = r.room_id
        WHERE r.timestamp >= ?
    """
    params: list[Any] = [_cutoff_iso(hours)]
    if room_name:
        query += " AND rm.room_name = ?"
        params.append(room_name)

    with get_connection(db_path) as conn:
        row = conn.execute(query, params).fetchone()

    result = _row_to_dict(row) or {}
    result["window_hours"] = hours
    result["room_name"] = room_name
    return result


def get_highest_co2_room(db_path: Path = DB_PATH) -> Optional[dict[str, Any]]:
    """Return the room with the highest most-recent CO2 reading."""
    query = """
        SELECT rm.room_name, r.co2, r.timestamp
        FROM hvac_readings r
        JOIN rooms rm ON rm.room_id = r.room_id
        WHERE r.co2 IS NOT NULL
          AND r.reading_id IN (
              SELECT MAX(reading_id) FROM hvac_readings GROUP BY room_id
          )
        ORDER BY r.co2 DESC
        LIMIT 1
    """
    with get_connection(db_path) as conn:
        row = conn.execute(query).fetchone()
    return _row_to_dict(row)


def get_weather(db_path: Path = DB_PATH) -> Optional[dict[str, Any]]:
    """Return the most recent weather observation."""
    query = "SELECT * FROM weather_data ORDER BY timestamp DESC LIMIT 1"
    with get_connection(db_path) as conn:
        row = conn.execute(query).fetchone()
    return _row_to_dict(row)


def list_rooms(db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    """Return every room, mainly useful for tooling/debugging."""
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM rooms").fetchall()
    return _rows_to_dicts(rows)


def list_devices(room_name: str | None = None, db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    """Return HVAC devices, optionally filtered to a single room."""
    query = """
        SELECT d.*, rm.room_name
        FROM hvac_devices d
        LEFT JOIN rooms rm ON rm.room_id = d.room_id
    """
    params: tuple[Any, ...] = ()
    if room_name:
        query += " WHERE rm.room_name = ?"
        params = (room_name,)
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return _rows_to_dicts(rows)
