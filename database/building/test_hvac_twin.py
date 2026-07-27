from database.building.hvac_twin import (
    HVACTwin,
    comfort_pmv,
    predict_comfort_and_load,
    simulate_hours,
)


def test_step_moves_temperature_toward_target_when_hot():
    twin = HVACTwin(target_temp_c=22.0, deadband_c=1.0, initial_temp_c=28.0)
    for _ in range(50):
        twin.step(dt_seconds=300, hour_of_day=15.0)
    assert twin.current_temp_c < 28.0
    assert twin.hvac_status in ("COOLING", "OFF")


def test_thermostat_turns_off_inside_deadband():
    twin = HVACTwin(target_temp_c=22.0, deadband_c=1.0, initial_temp_c=22.1)
    twin.update_thermostat()
    assert twin.hvac_status == "OFF"


def test_thermostat_heats_when_below_target():
    twin = HVACTwin(target_temp_c=22.0, deadband_c=1.0, initial_temp_c=18.0)
    state = twin.step(dt_seconds=300, hour_of_day=3.0)
    assert state["hvac_status"] == "HEATING"
    assert state["hvac_power_w"] > 0


def test_humidity_stays_within_bounds():
    twin = HVACTwin(initial_humidity_pct=55.0)
    for hour in range(0, 24):
        state = twin.step(dt_seconds=3600, hour_of_day=float(hour))
        assert 20.0 <= state["room_humidity_pct"] <= 95.0


def test_simulate_hours_yields_expected_step_count():
    states = list(simulate_hours(hours=2, dt_minutes=15, target_temp_c=22.0))
    assert len(states) == 8
    assert {"timestamp", "room_temp_c", "outside_temp_c", "hvac_status"} <= states[0].keys()


def test_comfort_pmv_neutral_at_target():
    assert comfort_pmv(22.0, 22.0) == 0.0


def test_comfort_pmv_clamped_to_scale():
    assert comfort_pmv(40.0, 22.0) == 3.0
    assert comfort_pmv(-10.0, 22.0) == -3.0


def test_predict_comfort_and_load_returns_expected_keys():
    result = predict_comfort_and_load(current_temp_c=26.0, target_temp_c=22.0, hour_of_day=15.0)
    assert set(result) == {"predicted_comfort_pmv", "predicted_load_kw"}
    assert result["predicted_load_kw"] >= 0
