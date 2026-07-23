"""Persistence for BMS control writes.

This is what makes the ``bms_write`` MCP tool operational instead of a
canned acknowledgement: it turns a ``(target, parameter, value)`` command
into real rows in ``building_data.db`` so that subsequent reads
(``building_queries``) reflect the change.

Only thermal parameters map onto this schema (buildings/rooms/hvac_*) —
non-thermal commands (e.g. a lighting ``lux`` write) are acknowledged but
have nothing to persist here, since this database is HVAC-scoped by
design. That's a deliberate boundary, not a missing feature: lighting/
access/safety domains will get their own tables when those subsystems
are wired up.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from database.building.init_building_db import DB_PATH, get_connection

_THERMAL_PARAMETERS = {"setpoint_c", "temperature", "temp_c", "supply_temp", "return_temp"}
_DEFAULT_BUILDING_NAME = "Default Building"


def _get_or_create_building(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT building_id FROM buildings WHERE building_name = ?",
        (_DEFAULT_BUILDING_NAME,),
    ).fetchone()
    if row is not None:
        return row["building_id"]
    cursor = conn.execute(
        "INSERT INTO buildings (building_name, location, floors, created_at) VALUES (?, ?, ?, ?)",
        (_DEFAULT_BUILDING_NAME, "unknown", 1, datetime.now(timezone.utc).isoformat()),
    )
    return cursor.lastrowid


def _get_or_create_room(conn: sqlite3.Connection, building_id: int, room_name: str) -> int:
    row = conn.execute("SELECT room_id FROM rooms WHERE room_name = ?", (room_name,)).fetchone()
    if row is not None:
        return row["room_id"]
    cursor = conn.execute(
        "INSERT INTO rooms (building_id, room_name, wing, floor, area, capacity) VALUES (?, ?, NULL, NULL, NULL, NULL)",
        (building_id, room_name),
    )
    return cursor.lastrowid


def _get_or_create_device(conn: sqlite3.Connection, room_id: int, device_name: str) -> int:
    row = conn.execute("SELECT device_id FROM hvac_devices WHERE device_name = ?", (device_name,)).fetchone()
    if row is not None:
        return row["device_id"]
    cursor = conn.execute(
        "INSERT INTO hvac_devices (room_id, device_name, device_type, status, rated_power) "
        "VALUES (?, ?, 'hvac_unit', 'active', NULL)",
        (room_id, device_name),
    )
    return cursor.lastrowid


def apply_bms_command(
    target: str,
    parameter: str,
    value: Optional[float],
    db_path: Path = DB_PATH,
) -> dict[str, Any]:
    """Persist a BMS control command against the building database.

    ``target`` is used as both the room and device identifier: if a room
    or device with that name does not exist yet it is created on demand,
    so the digital twin state grows to cover whatever the agents send it
    rather than silently dropping unknown targets.

    Returns a dict describing what happened. Never raises: failures come
    back as ``{"success": False, "error": ...}`` so the calling MCP tool
    can still return a well-formed response to the LLM.
    """
    target_name = (target or "").strip() or "unknown-target"
    parameter_key = (parameter or "").strip().lower()

    if parameter_key not in _THERMAL_PARAMETERS or value is None:
        return {
            "success": True,
            "persisted": False,
            "reason": (
                f"parameter '{parameter}' is outside the HVAC schema "
                "(buildings/rooms/hvac_devices/hvac_readings); acknowledged only"
            ),
        }

    now = datetime.now(timezone.utc).isoformat()
    try:
        with get_connection(db_path) as conn:
            building_id = _get_or_create_building(conn)
            room_id = _get_or_create_room(conn, building_id, target_name)
            device_id = _get_or_create_device(conn, room_id, target_name)

            conn.execute(
                "UPDATE hvac_devices SET status = 'active' WHERE device_id = ?",
                (device_id,),
            )
            conn.execute(
                """
                INSERT INTO hvac_readings (
                    device_id, room_id, timestamp, temperature, supply_temp, hvac_mode
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (device_id, room_id, now, float(value), float(value), "bms_write"),
            )
            conn.commit()
    except sqlite3.Error as exc:
        return {"success": False, "persisted": False, "error": str(exc)}

    return {
        "success": True,
        "persisted": True,
        "building_id": building_id,
        "room_id": room_id,
        "device_id": device_id,
        "timestamp": now,
        "written_value": value,
    }
