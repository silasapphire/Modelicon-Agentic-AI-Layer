"""Ingestion of HVAC time-series data into ``building_data.db``.

The HuggingFace dataset ``YUSHU-AI/HVAC-simulate-time-series-data`` is a
*temporary* data source, standing in until another intern's Digital Twin
is wired up. Everything HuggingFace-specific is isolated to
``HF_COLUMN_MAP`` and ``_iter_hf_rows`` below.

``ingest_rows`` — the part that actually writes to SQLite — knows
nothing about HuggingFace. It takes an iterable of plain dicts already
using the canonical column names, which is exactly what a future
``ingest_digital_twin.py`` would also produce. Swapping data sources
later means writing a new row-iterator function; the schema and the
insert logic never change.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

from database.building.init_building_db import DB_PATH, get_connection

logger = logging.getLogger(__name__)

HF_DATASET_NAME = "YUSHU-AI/HVAC-simulate-time-series-data"

#: Canonical hvac_readings/room/device column -> candidate source column
#: names in the HF dataset, tried in order. This is the only place that
#: knows about the HuggingFace schema; everything downstream only ever
#: sees the canonical keys on the left.
HF_COLUMN_MAP: dict[str, tuple[str, ...]] = {
    "timestamp": ("timestamp", "time", "datetime", "date"),
    "temperature": ("temperature", "temp", "indoor_temp", "room_temp"),
    "humidity": ("humidity", "rh", "relative_humidity"),
    "co2": ("co2", "co2_ppm", "CO2"),
    "occupancy": ("occupancy", "occupied", "occupancy_status"),
    "airflow": ("airflow", "air_flow", "flow_rate"),
    "pressure": ("pressure", "static_pressure"),
    "power_kw": ("power_kw", "power", "power_consumption", "power_kW"),
    "energy_kwh": ("energy_kwh", "energy", "energy_consumption", "energy_kWh"),
    "supply_temp": ("supply_temp", "supply_air_temp", "sat"),
    "return_temp": ("return_temp", "return_air_temp", "rat"),
    "hvac_mode": ("hvac_mode", "mode", "system_mode"),
    "device_name": ("device_name", "device", "device_id", "unit_id", "ahu_id"),
    "room_name": ("room_name", "room", "zone", "zone_id"),
}

_READING_COLUMNS = (
    "temperature",
    "humidity",
    "co2",
    "occupancy",
    "airflow",
    "pressure",
    "power_kw",
    "energy_kwh",
    "supply_temp",
    "return_temp",
    "hvac_mode",
)

_DEFAULT_BUILDING_NAME = "HF Import Building"
_DEFAULT_ROOM_NAME = "hf-import"
_DEFAULT_DEVICE_NAME = "hf-import-device"


def map_hf_record(raw: dict[str, Any]) -> dict[str, Any]:
    """Translate one raw HF dataset record into the canonical schema.

    Missing source columns simply produce a missing (not errored) key —
    callers treat absent keys as ``NULL``. This keeps ingestion resilient
    to dataset revisions that add/drop/rename columns.
    """
    mapped: dict[str, Any] = {}
    for canonical, candidates in HF_COLUMN_MAP.items():
        for candidate in candidates:
            if candidate in raw and raw[candidate] is not None:
                mapped[canonical] = raw[candidate]
                break
    return mapped


def _iter_hf_rows(
    dataset_name: str = HF_DATASET_NAME,
    split: str = "train",
    limit: Optional[int] = None,
) -> Iterator[dict[str, Any]]:
    """Yield canonical-schema dicts from the HuggingFace dataset.

    Requires the optional ``datasets`` package. Raises ``RuntimeError``
    with an actionable message if it isn't installed, rather than a bare
    ``ImportError`` deep in a stack trace.
    """
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError(
            "The 'datasets' package is required for HuggingFace ingestion. "
            "Install it with `pip install datasets` (or point ingest_hf at "
            "another row source once the Digital Twin is available)."
        ) from exc

    dataset = load_dataset(dataset_name, split=split, streaming=True)
    for i, raw in enumerate(dataset):
        if limit is not None and i >= limit:
            break
        yield map_hf_record(dict(raw))


def _get_or_create_building(conn, name: str) -> int:
    row = conn.execute("SELECT building_id FROM buildings WHERE building_name = ?", (name,)).fetchone()
    if row is not None:
        return row["building_id"]
    cursor = conn.execute(
        "INSERT INTO buildings (building_name, location, floors, created_at) VALUES (?, ?, ?, ?)",
        (name, "unknown", 1, datetime.now(timezone.utc).isoformat()),
    )
    return cursor.lastrowid


def _get_or_create_room(conn, building_id: int, name: str) -> int:
    row = conn.execute("SELECT room_id FROM rooms WHERE room_name = ?", (name,)).fetchone()
    if row is not None:
        return row["room_id"]
    cursor = conn.execute(
        "INSERT INTO rooms (building_id, room_name, wing, floor, area, capacity) VALUES (?, ?, NULL, NULL, NULL, NULL)",
        (building_id, name),
    )
    return cursor.lastrowid


def _get_or_create_device(conn, room_id: int, name: str) -> int:
    row = conn.execute("SELECT device_id FROM hvac_devices WHERE device_name = ?", (name,)).fetchone()
    if row is not None:
        return row["device_id"]
    cursor = conn.execute(
        "INSERT INTO hvac_devices (room_id, device_name, device_type, status, rated_power) "
        "VALUES (?, ?, 'hvac_unit', 'active', NULL)",
        (room_id, name),
    )
    return cursor.lastrowid


def ingest_rows(
    rows: Iterable[dict[str, Any]],
    db_path: Path = DB_PATH,
    default_room_name: str = _DEFAULT_ROOM_NAME,
    default_device_name: str = _DEFAULT_DEVICE_NAME,
) -> int:
    """Insert canonical-schema rows into ``hvac_readings``.

    Source-agnostic: this is what a future Digital Twin ingestion module
    calls too, once it produces rows with the same canonical keys used by
    ``map_hf_record``. Rows missing a ``timestamp`` are skipped (the
    column is ``NOT NULL``) and counted as errors in the log, not raised.
    """
    inserted = 0
    with get_connection(db_path) as conn:
        building_id = _get_or_create_building(conn, _DEFAULT_BUILDING_NAME)
        room_cache: dict[str, int] = {}
        device_cache: dict[str, int] = {}

        for row in rows:
            timestamp = row.get("timestamp")
            if not timestamp:
                logger.warning("skipping row with no timestamp: %s", row)
                continue
            if isinstance(timestamp, (int, float)):
                timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
            else:
                timestamp = str(timestamp)

            room_name = str(row.get("room_name") or default_room_name)
            device_name = str(row.get("device_name") or default_device_name)

            if room_name not in room_cache:
                room_cache[room_name] = _get_or_create_room(conn, building_id, room_name)
            room_id = room_cache[room_name]

            if device_name not in device_cache:
                device_cache[device_name] = _get_or_create_device(conn, room_id, device_name)
            device_id = device_cache[device_name]

            values = [row.get(col) for col in _READING_COLUMNS]
            conn.execute(
                f"""
                INSERT INTO hvac_readings (
                    device_id, room_id, timestamp, {", ".join(_READING_COLUMNS)}
                ) VALUES (?, ?, ?, {", ".join("?" for _ in _READING_COLUMNS)})
                """,
                (device_id, room_id, timestamp, *values),
            )
            inserted += 1

        conn.commit()

    return inserted


def ingest_from_huggingface(
    dataset_name: str = HF_DATASET_NAME,
    split: str = "train",
    limit: Optional[int] = None,
    db_path: Path = DB_PATH,
) -> int:
    """Load rows from the HuggingFace dataset and persist them.

    Returns the number of rows inserted. Any failure to reach/parse the
    dataset (missing package, network error, unexpected schema) is
    logged and re-raised as ``RuntimeError`` so callers can decide how to
    degrade (e.g. fall back to whatever data is already in the DB).
    """
    try:
        rows = list(_iter_hf_rows(dataset_name=dataset_name, split=split, limit=limit))
    except RuntimeError:
        raise
    except Exception as exc:  # pragma: no cover - network/dataset failures
        raise RuntimeError(f"failed to load HuggingFace dataset '{dataset_name}': {exc}") from exc

    return ingest_rows(rows, db_path=db_path)


if __name__ == "__main__":
    count = ingest_from_huggingface(limit=1000)
    print(f"ingested {count} row(s) into {DB_PATH}")
