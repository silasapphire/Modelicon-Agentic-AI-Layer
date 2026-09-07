"""Ingestion of HVAC time-series data from the OpenModelica digital twin.

Replaces ``ingest_hf.py`` (the temporary HuggingFace stand-in) and
``seed_topology.py`` (the synthetic per-room generator) now that a real
physics-based FMU exists at ``Building_1/HVAC.fmu``. That FMU models one
zone -- see ``database.building.topology`` -- so this module writes one
room's worth of genuinely-simulated readings instead of nine rooms of
synthetic ones.

Two things get produced by running this module directly
(``python -m database.building.ingest_fmu``):

1. A 24h simulation at the model's default setpoint, aggregated to one
   row per hour and written into ``hvac_readings``/``weather_data`` via
   ``ingest_rows`` -- the schema-agnostic insert logic, structurally
   identical to what ``ingest_hf.py`` used, just fed from the FMU
   instead of HuggingFace.
2. A short simulation at each candidate setpoint (16-30C), averaging
   power draw over each run, cached to ``fmu_power_lookup.json``. This
   replaces the old hardcoded ``_POWER_LOOKUP_C`` fiction in
   ``mcp_server/server.py`` with genuine FMU-derived numbers, in real
   kW rather than the previous placeholder "mW" unit.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

import numpy as np
import pandas as pd
from fmpy import simulate_fmu

from database.building.init_building_db import DB_PATH, get_connection, init_building_db
from database.building.topology import BUILDING_NAME, DEVICE_NAME, ZONE_NAME

logger = logging.getLogger(__name__)

FMU_PATH: Path = Path(__file__).resolve().parent.parent.parent / "Building_1" / "HVAC.fmu"
POWER_LOOKUP_PATH: Path = Path(__file__).resolve().parent / "fmu_power_lookup.json"

_KELVIN_OFFSET = 273.15
_READING_COLUMNS = (
    "temperature", "humidity", "co2", "occupancy", "airflow", "pressure",
    "power_kw", "energy_kwh", "supply_temp", "return_temp", "hvac_mode",
)
_SETPOINTS_C = tuple(range(16, 31))  # matches the old lookup table's range


def _k_to_c(kelvin: float) -> float:
    return round(kelvin - _KELVIN_OFFSET, 2)


# ---------------------------------------------------------------------
# Schema-agnostic row insertion -- moved here from the now-removed
# ingest_hf.py, unchanged. Still knows nothing about where rows come
# from; any future data source can reuse it the same way.
# ---------------------------------------------------------------------

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
    room_name: str = ZONE_NAME,
    device_name: str = DEVICE_NAME,
) -> int:
    """Insert canonical-schema rows into ``hvac_readings``. Source-agnostic:
    rows just need the canonical keys in ``_READING_COLUMNS`` plus a
    ``timestamp``. Rows missing a timestamp are skipped and logged, not
    raised."""
    inserted = 0
    with get_connection(db_path) as conn:
        building_id = _get_or_create_building(conn, BUILDING_NAME)
        room_id = _get_or_create_room(conn, building_id, room_name)
        device_id = _get_or_create_device(conn, room_id, device_name)

        for row in rows:
            timestamp = row.get("timestamp")
            if not timestamp:
                logger.warning("skipping row with no timestamp: %s", row)
                continue
            timestamp = timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp)

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


def _ingest_weather_rows(rows: Iterable[dict[str, Any]], db_path: Path = DB_PATH) -> int:
    inserted = 0
    with get_connection(db_path) as conn:
        for row in rows:
            conn.execute(
                "INSERT INTO weather_data (timestamp, outdoor_temperature, humidity, wind_speed, condition) "
                "VALUES (?, ?, ?, ?, ?)",
                (row["timestamp"], row["outdoor_temperature"], None, None, None),
            )
            inserted += 1
        conn.commit()
    return inserted


# ---------------------------------------------------------------------
# FMU simulation
# ---------------------------------------------------------------------

def run_fmu_simulation(
    fmu_path: Path = FMU_PATH,
    stop_time: float = 86400,
    output_interval: float = 10,
    start_values: Optional[dict[str, float]] = None,
) -> pd.DataFrame:
    """Run the digital twin and return the raw high-resolution trace."""
    result = simulate_fmu(
        filename=str(fmu_path),
        start_time=0,
        stop_time=stop_time,
        output_interval=output_interval,
        start_values=start_values or {},
    )
    return pd.DataFrame(result)


def _hourly_rows(df: pd.DataFrame, start: datetime) -> Iterator[dict[str, Any]]:
    """Aggregate a raw FMU trace into one canonical-schema row per hour --
    same trapezoidal-energy approach as the reference plotting script,
    just producing DB rows instead of a CSV."""
    for hour in range(24):
        window = df[(df["time"] >= hour * 3600) & (df["time"] <= (hour + 1) * 3600)]
        if len(window) < 2:
            continue

        t_hours = window["time"].to_numpy() / 3600
        power_kw = window["totalElectricPower_kW"].to_numpy()
        energy_kwh = float(np.trapezoid(power_kw, t_hours))
        heating_on = window["heatingCommand"].mean() > 0.5

        yield {
            "timestamp": (start + timedelta(hours=hour)).isoformat(),
            "temperature": _k_to_c(window["roomTemperature"].mean()),
            "humidity": None,
            "co2": None,
            "occupancy": round(window["occupancyPersons"].mean(), 1),
            "airflow": round(window["airMassFlow"].mean(), 4),
            "pressure": None,
            "power_kw": round(float(power_kw.mean()), 4),
            "energy_kwh": round(energy_kwh, 4),
            "supply_temp": _k_to_c(window["supplyAirTemperature"].mean()),
            # Closest available proxy for a return-air sensor: the fan
            # inlet is post-heat-recovery mixed air, not a literal duct
            # return sensor -- the FMU doesn't expose one directly.
            "return_temp": _k_to_c(window["fanInletTemperature"].mean()),
            "hvac_mode": "heating" if heating_on else "cooling",
        }


def _weather_rows(df: pd.DataFrame, start: datetime) -> Iterator[dict[str, Any]]:
    for hour in range(24):
        window = df[(df["time"] >= hour * 3600) & (df["time"] <= (hour + 1) * 3600)]
        if len(window) < 2:
            continue
        yield {
            "timestamp": (start + timedelta(hours=hour)).isoformat(),
            "outdoor_temperature": _k_to_c(window["outdoorTemperature"].mean()),
        }


def ingest_zone_readings(db_path: Path = DB_PATH, fmu_path: Path = FMU_PATH) -> dict[str, int]:
    """Run the 24h default-setpoint simulation and load it into the DB,
    ending now (UTC) -- the same "backfill ending now" shape
    ``seed_topology.py`` used, just FMU-sourced."""
    init_building_db(db_path)
    df = run_fmu_simulation(fmu_path=fmu_path, stop_time=86400, output_interval=10)
    start = datetime.now(timezone.utc) - timedelta(hours=24)

    readings_inserted = ingest_rows(_hourly_rows(df, start), db_path=db_path)
    weather_inserted = _ingest_weather_rows(_weather_rows(df, start), db_path=db_path)

    return {"readings": readings_inserted, "weather": weather_inserted}


def run_setpoint_sweep(
    fmu_path: Path = FMU_PATH,
    setpoints_c: tuple[int, ...] = _SETPOINTS_C,
    window_seconds: float = 1800,
) -> dict[str, float]:
    """Re-run the FMU once per candidate setpoint (a short window each,
    not the full 24h) and record the average power draw at each -- a
    genuine physics-derived replacement for the old hardcoded
    temperature-to-power lookup table."""
    lookup: dict[str, float] = {}
    for setpoint_c in setpoints_c:
        df = run_fmu_simulation(
            fmu_path=fmu_path,
            stop_time=window_seconds,
            # A coarser communication step (e.g. 60s) makes this stiff
            # DAE's co-simulation diverge at extreme setpoints -- 10s is
            # the step size already confirmed stable for a full 24h run.
            output_interval=10,
            start_values={"TSetRoo.k": setpoint_c + _KELVIN_OFFSET},
        )
        lookup[str(setpoint_c)] = round(float(df["totalElectricPower_kW"].mean()), 4)
    return lookup


def cache_power_lookup(path: Path = POWER_LOOKUP_PATH, **sweep_kwargs) -> dict[str, float]:
    lookup = run_setpoint_sweep(**sweep_kwargs)
    path.write_text(json.dumps(lookup, indent=2))
    return lookup


def load_power_lookup(path: Path = POWER_LOOKUP_PATH) -> Optional[dict[str, float]]:
    """Read the cached sweep result, or None if it hasn't been generated
    yet (fresh checkout before ``ingest_fmu`` has been run once)."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


if __name__ == "__main__":
    if not FMU_PATH.exists():
        raise SystemExit(
            f"FMU not found at {FMU_PATH}. Export it from Building_1/HVAC.mo "
            "via OMEdit (or omc) first."
        )

    print(f"Simulating {FMU_PATH.name} for 24h and loading readings...")
    summary = ingest_zone_readings()
    print(f"  inserted {summary['readings']} hourly reading(s), {summary['weather']} weather row(s)")

    print(f"Sweeping {len(_SETPOINTS_C)} candidate setpoints for the power lookup table...")
    lookup = cache_power_lookup()
    print(f"  cached to {POWER_LOOKUP_PATH}: {lookup}")
