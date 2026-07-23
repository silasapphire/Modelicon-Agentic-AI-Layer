"""Schema creation for the building data database.

Run this module directly (``python -m database.building.init_building_db``)
to (re)create ``building_data.db`` with an empty schema. Safe to re-run:
every statement uses ``CREATE TABLE IF NOT EXISTS``.

The schema is intentionally source-agnostic. It describes buildings,
rooms, HVAC devices, their readings, and weather — nothing here is tied
to the HuggingFace dataset used for the initial data load. Whatever
Digital Twin eventually replaces that dataset writes into the same
tables through ``building_queries.py``.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH: Path = Path(__file__).resolve().parent / "building_data.db"

_SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS buildings (
        building_id   INTEGER PRIMARY KEY,
        building_name TEXT,
        location      TEXT,
        floors        INTEGER,
        created_at    TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS rooms (
        room_id     INTEGER PRIMARY KEY,
        building_id INTEGER,
        room_name   TEXT,
        wing        TEXT,
        floor       INTEGER,
        area        REAL,
        capacity    INTEGER,
        FOREIGN KEY (building_id) REFERENCES buildings (building_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS hvac_devices (
        device_id   INTEGER PRIMARY KEY,
        room_id     INTEGER,
        device_name TEXT,
        device_type TEXT,
        status      TEXT,
        rated_power REAL,
        FOREIGN KEY (room_id) REFERENCES rooms (room_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS hvac_readings (
        reading_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id    INTEGER,
        room_id      INTEGER,
        timestamp    TEXT NOT NULL,
        temperature  REAL,
        humidity     REAL,
        co2          REAL,
        occupancy    INTEGER,
        airflow      REAL,
        pressure     REAL,
        power_kw     REAL,
        energy_kwh   REAL,
        supply_temp  REAL,
        return_temp  REAL,
        hvac_mode    TEXT,
        FOREIGN KEY (device_id) REFERENCES hvac_devices (device_id),
        FOREIGN KEY (room_id) REFERENCES rooms (room_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS weather_data (
        weather_id          INTEGER PRIMARY KEY,
        timestamp            TEXT,
        outdoor_temperature  REAL,
        humidity             REAL,
        wind_speed           REAL,
        condition             TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_hvac_readings_timestamp ON hvac_readings (timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_hvac_readings_device ON hvac_readings (device_id)",
    "CREATE INDEX IF NOT EXISTS idx_hvac_readings_room ON hvac_readings (room_id)",
    "CREATE INDEX IF NOT EXISTS idx_weather_data_timestamp ON weather_data (timestamp)",
)


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open a connection to the building database with sane defaults.

    Foreign keys are off by default in SQLite, so every connection this
    package hands out turns them on explicitly. Rows are returned as
    ``sqlite3.Row`` so callers can build plain dictionaries from them.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_building_db(db_path: Path = DB_PATH) -> None:
    """Create every table (and index) in the building schema if missing."""
    with get_connection(db_path) as conn:
        for statement in _SCHEMA_STATEMENTS:
            conn.execute(statement)
        conn.commit()


if __name__ == "__main__":
    init_building_db()
    print(f"building database initialised at {DB_PATH}")
