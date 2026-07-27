"""Seeds a fixed building topology (1 building, 3 floors, 3 rooms/floor)
and populates each room with an HVAC time-series history.

The HuggingFace dataset ``ingest_hf.py`` points at
(``YUSHU-AI/HVAC-simulate-time-series-data``) does not actually contain
usable HVAC columns (verified live: its only fields are ``id`` and a
column literally named ``83``) -- so this module generates a synthetic
but realistic per-room time series instead, using the exact canonical
schema ``ingest_rows`` already expects. Swapping in a real dataset or a
Digital Twin feed later only means writing a different row source; the
topology and ``ingest_rows`` call below stay the same.
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from database.building.ingest_hf import ingest_rows
from database.building.init_building_db import DB_PATH, get_connection, init_building_db
from database.building.topology import BUILDING_NAME, FLOORS, ROOM_ROSTER


def _get_or_create_building(conn, name: str) -> int:
    row = conn.execute("SELECT building_id FROM buildings WHERE building_name = ?", (name,)).fetchone()
    if row is not None:
        return row["building_id"]
    cursor = conn.execute(
        "INSERT INTO buildings (building_name, location, floors, created_at) VALUES (?, ?, ?, ?)",
        (name, "unknown", len(FLOORS), datetime.now(timezone.utc).isoformat()),
    )
    return cursor.lastrowid


def _get_or_create_room(conn, building_id: int, room_name: str, floor: int) -> int:
    row = conn.execute("SELECT room_id FROM rooms WHERE room_name = ?", (room_name,)).fetchone()
    if row is not None:
        conn.execute("UPDATE rooms SET floor = ? WHERE room_id = ?", (floor, row["room_id"]))
        return row["room_id"]
    cursor = conn.execute(
        "INSERT INTO rooms (building_id, room_name, wing, floor, area, capacity) VALUES (?, ?, NULL, ?, NULL, NULL)",
        (building_id, room_name, floor),
    )
    return cursor.lastrowid


def _get_or_create_device(conn, room_id: int, device_name: str) -> int:
    row = conn.execute("SELECT device_id FROM hvac_devices WHERE device_name = ?", (device_name,)).fetchone()
    if row is not None:
        return row["device_id"]
    cursor = conn.execute(
        "INSERT INTO hvac_devices (room_id, device_name, device_type, status, rated_power) "
        "VALUES (?, ?, 'hvac_unit', 'active', NULL)",
        (room_id, device_name),
    )
    return cursor.lastrowid


def ensure_topology(db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    """Create (or update) the building/rooms/devices for ROOM_ROSTER.

    Idempotent: re-running this only fills in missing rows and corrects
    ``floor`` on existing rooms, it never duplicates or deletes.
    Returns ROOM_ROSTER enriched with the resolved room_id/device_id.
    """
    init_building_db(db_path)
    resolved = []
    with get_connection(db_path) as conn:
        building_id = _get_or_create_building(conn, BUILDING_NAME)
        for room in ROOM_ROSTER:
            room_id = _get_or_create_room(conn, building_id, room["room_name"], room["floor"])
            device_id = _get_or_create_device(conn, room_id, room["device_name"])
            resolved.append({**room, "building_id": building_id, "room_id": room_id, "device_id": device_id})
        conn.commit()
    return resolved


def _generate_room_series(room: dict[str, Any], hours: int, start: datetime) -> Iterator[dict[str, Any]]:
    """Yield one canonical-schema hvac_readings row per hour for a room.

    Not meant to be physically rigorous -- just varied enough per room
    (via a per-room random seed and a floor offset) to be useful for
    exercising per-room queries and the thermal agent, until a real
    Digital Twin feed replaces it.
    """
    rng = random.Random(f"{room['room_name']}::{room['device_name']}")
    floor_offset_c = (room["floor"] - 2) * 0.6          # higher floors run slightly warmer
    base_temp_c = 22.5 + floor_offset_c
    base_co2 = 480 + room["floor"] * 20

    for i in range(hours):
        ts = start + timedelta(hours=i)
        hour_of_day = ts.hour + ts.minute / 60
        occupied = 8 <= hour_of_day < 19

        # Diurnal swing (warmer mid-afternoon) + small random jitter.
        diurnal_c = 1.4 * math.sin((hour_of_day - 9) / 24 * 2 * math.pi)
        temp_c = round(base_temp_c + diurnal_c + rng.uniform(-0.3, 0.3), 2)

        occupancy = rng.randint(3, 14) if occupied else rng.randint(0, 1)
        co2 = round(base_co2 + occupancy * 18 + rng.uniform(-15, 15), 1)
        humidity = round(45 + rng.uniform(-5, 5), 1)
        power_kw = round(2.0 + abs(diurnal_c) * 1.1 + occupancy * 0.08 + rng.uniform(-0.15, 0.15), 2)
        energy_kwh = round(power_kw * 1.0, 2)  # 1-hour buckets -> kWh == kW

        yield {
            "timestamp": ts.isoformat(),
            "room_name": room["room_name"],
            "device_name": room["device_name"],
            "temperature": temp_c,
            "humidity": humidity,
            "co2": co2,
            "occupancy": occupancy,
            "power_kw": power_kw,
            "energy_kwh": energy_kwh,
            "supply_temp": round(temp_c - 1.5, 2),
            "return_temp": round(temp_c + 0.8, 2),
            "hvac_mode": "cooling" if diurnal_c > 0 else "heating",
        }


def seed_all(db_path: Path = DB_PATH, hours: int = 48, start: datetime | None = None) -> dict[str, int]:
    """Ensure the 9-room topology exists and backfill each room with
    ``hours`` hours of synthetic time-series data, ending now (UTC).

    Returns {"rooms": 9, "readings": 9 * hours}.
    """
    start = start or (datetime.now(timezone.utc) - timedelta(hours=hours))
    rooms = ensure_topology(db_path)

    total_inserted = 0
    for room in rooms:
        rows = list(_generate_room_series(room, hours=hours, start=start))
        total_inserted += ingest_rows(rows, db_path=db_path)

    return {"rooms": len(rooms), "readings": total_inserted}


if __name__ == "__main__":
    summary = seed_all()
    print(f"seeded {summary['rooms']} rooms across {len(FLOORS)} floors, "
          f"{summary['readings']} hourly reading(s) into {DB_PATH}")
