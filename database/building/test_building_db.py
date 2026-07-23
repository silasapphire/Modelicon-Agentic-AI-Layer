from database.building.building_queries import (
    get_energy_usage,
    get_highest_co2_room,
    get_last_24h_average,
    get_latest_sensor_data,
    get_room_temperature,
    get_weather,
)
from database.building.building_writes import apply_bms_command
from database.building.init_building_db import init_building_db
from database.building.ingest_hf import ingest_rows, map_hf_record


def _seed(db_path):
    init_building_db(db_path)
    with_conn_kwargs = {"db_path": db_path}
    rows = [
        {
            "timestamp": "2026-07-23T06:00:00+00:00",
            "room_name": "Lab A",
            "device_name": "AHU-1",
            "temperature": 22.5,
            "humidity": 44.0,
            "co2": 520.0,
            "power_kw": 3.1,
            "energy_kwh": 0.8,
        },
        {
            "timestamp": "2026-07-23T07:00:00+00:00",
            "room_name": "Lab A",
            "device_name": "AHU-1",
            "temperature": 23.0,
            "humidity": 45.0,
            "co2": 610.0,
            "power_kw": 3.4,
            "energy_kwh": 0.9,
        },
        {
            "timestamp": "2026-07-23T07:00:00+00:00",
            "room_name": "Server Room",
            "device_name": "CRAC-1",
            "temperature": 19.0,
            "humidity": 30.0,
            "co2": 900.0,
            "power_kw": 5.0,
            "energy_kwh": 1.2,
        },
    ]
    ingest_rows(rows, **with_conn_kwargs)
    return rows


def test_init_building_db_creates_expected_tables(tmp_path):
    db_path = tmp_path / "building_data.db"
    init_building_db(db_path)

    import sqlite3

    with sqlite3.connect(db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"buildings", "rooms", "hvac_devices", "hvac_readings", "weather_data"} <= tables


def test_ingest_rows_and_latest_sensor_data(tmp_path):
    db_path = tmp_path / "building_data.db"
    _seed(db_path)

    latest = get_latest_sensor_data(db_path=db_path)
    assert latest is not None
    assert isinstance(latest, dict)


def test_get_room_temperature_returns_most_recent(tmp_path):
    db_path = tmp_path / "building_data.db"
    _seed(db_path)

    result = get_room_temperature("Lab A", db_path=db_path)
    assert result["temperature"] == 23.0


def test_get_highest_co2_room(tmp_path):
    db_path = tmp_path / "building_data.db"
    _seed(db_path)

    result = get_highest_co2_room(db_path=db_path)
    assert result["room_name"] == "Server Room"


def test_get_energy_usage_sums_window(tmp_path):
    db_path = tmp_path / "building_data.db"
    _seed(db_path)

    result = get_energy_usage(room_name="Lab A", hours=999999, db_path=db_path)
    assert result["sample_count"] == 2
    assert round(result["total_energy_kwh"], 2) == 1.7


def test_get_last_24h_average_empty_db_returns_none_values(tmp_path):
    db_path = tmp_path / "building_data.db"
    init_building_db(db_path)

    result = get_last_24h_average(db_path=db_path)
    assert result["sample_count"] == 0
    assert result["avg_temperature"] is None


def test_get_weather_returns_latest(tmp_path):
    db_path = tmp_path / "building_data.db"
    init_building_db(db_path)
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO weather_data (timestamp, outdoor_temperature, humidity, wind_speed, condition) "
            "VALUES (?, ?, ?, ?, ?)",
            ("2026-07-23T06:00:00+00:00", 30.0, 60.0, 5.0, "sunny"),
        )
        conn.commit()

    result = get_weather(db_path=db_path)
    assert result["condition"] == "sunny"


def test_map_hf_record_handles_missing_columns():
    mapped = map_hf_record({"temp": 21.5, "room": "Lab A"})
    assert mapped["temperature"] == 21.5
    assert mapped["room_name"] == "Lab A"
    assert "co2" not in mapped


def test_apply_bms_command_persists_thermal_write(tmp_path):
    db_path = tmp_path / "building_data.db"
    init_building_db(db_path)

    result = apply_bms_command("Lab A", "setpoint_c", 20.0, db_path=db_path)
    assert result["success"] is True
    assert result["persisted"] is True

    room_temp = get_room_temperature("Lab A", db_path=db_path)
    assert room_temp["temperature"] == 20.0


def test_apply_bms_command_acknowledges_non_thermal_without_persisting(tmp_path):
    db_path = tmp_path / "building_data.db"
    init_building_db(db_path)

    result = apply_bms_command("lighting", "lux", 400, db_path=db_path)
    assert result["success"] is True
    assert result["persisted"] is False
