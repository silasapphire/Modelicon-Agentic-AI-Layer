"""Physics-based HVAC digital twin.

A lumped thermal-resistance/capacitance (R/C) model of a room and its
HVAC system. This is the "Digital Twin" referenced in
``init_building_db.py`` -- it replaces the previously hardcoded
``modelica_sim`` stub in ``mcp_server/server.py`` with a real, if
simplified, simulation, and backs the Digital Twin panel in the
dashboard.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any, Iterator, Optional


class HVACTwin:
    """Simulates a single room's temperature/humidity under thermostat control."""

    def __init__(
        self,
        target_temp_c: float = 22.0,
        deadband_c: float = 1.0,
        initial_temp_c: float = 24.0,
        initial_humidity_pct: float = 55.0,
        thermal_resistance: float = 0.15,
        thermal_mass: float = 1500.0,
        internal_heat_load_w: float = 500.0,
        cooling_capacity_w: float = -3500.0,
        heating_capacity_w: float = 3000.0,
    ):
        self.thermal_resistance = thermal_resistance
        self.thermal_mass = thermal_mass
        self.internal_heat_load_w = internal_heat_load_w
        self.cooling_capacity_w = cooling_capacity_w
        self.heating_capacity_w = heating_capacity_w

        self.target_temp_c = target_temp_c
        self.deadband_c = deadband_c

        self.current_temp_c = initial_temp_c
        self.current_humidity_pct = initial_humidity_pct
        self.hvac_status = "OFF"

    def get_outside_conditions(self, hour_of_day: float) -> tuple[float, float]:
        """Outside temp/humidity as a 24h sine wave peaking at 15:00, trough at 03:00."""
        outside_temp_c = 20.0 + 10.0 * math.sin((hour_of_day - 9.0) * (math.pi / 12.0))
        outside_humidity_pct = 60.0 - 15.0 * math.sin((hour_of_day - 9.0) * (math.pi / 12.0))
        return outside_temp_c, outside_humidity_pct

    def update_thermostat(self) -> None:
        if self.current_temp_c > self.target_temp_c + self.deadband_c:
            self.hvac_status = "COOLING"
        elif self.current_temp_c < self.target_temp_c - self.deadband_c:
            self.hvac_status = "HEATING"
        elif self.target_temp_c - (self.deadband_c * 0.5) <= self.current_temp_c <= self.target_temp_c + (self.deadband_c * 0.5):
            self.hvac_status = "OFF"

    def step(self, dt_seconds: float, hour_of_day: float) -> dict[str, Any]:
        outside_temp_c, outside_humidity_pct = self.get_outside_conditions(hour_of_day)
        self.update_thermostat()

        hvac_power_w = 0.0
        if self.hvac_status == "COOLING":
            hvac_power_w = self.cooling_capacity_w
        elif self.hvac_status == "HEATING":
            hvac_power_w = self.heating_capacity_w

        # Euler integration of heat transfer: dT = (net heat flow * dt) / thermal mass
        heat_from_outside_w = (outside_temp_c - self.current_temp_c) / self.thermal_resistance
        net_heat_flow_w = heat_from_outside_w + self.internal_heat_load_w + hvac_power_w
        self.current_temp_c += (net_heat_flow_w * dt_seconds) / (self.thermal_mass * 1000)

        self.current_humidity_pct += (outside_humidity_pct - self.current_humidity_pct) * 0.005
        if self.hvac_status == "COOLING":
            self.current_humidity_pct -= 0.05 * (dt_seconds / 60.0)
        self.current_humidity_pct = max(20.0, min(self.current_humidity_pct, 95.0))

        return {
            "outside_temp_c": round(outside_temp_c, 2),
            "outside_humidity_pct": round(outside_humidity_pct, 2),
            "room_temp_c": round(self.current_temp_c, 2),
            "room_humidity_pct": round(self.current_humidity_pct, 2),
            "hvac_status": self.hvac_status,
            "hvac_power_w": hvac_power_w,
            "target_temp_c": self.target_temp_c,
        }


def simulate_hours(
    hours: float = 24,
    dt_minutes: float = 5,
    start_time: Optional[datetime] = None,
    target_temp_c: float = 22.5,
    initial_temp_c: float = 24.0,
    **twin_kwargs: Any,
) -> Iterator[dict[str, Any]]:
    """Yield one twin state per ``dt_minutes`` step across ``hours``, starting at ``start_time``."""
    twin = HVACTwin(target_temp_c=target_temp_c, initial_temp_c=initial_temp_c, **twin_kwargs)
    start_time = start_time or datetime.now().replace(minute=0, second=0, microsecond=0)
    current_time = start_time
    steps = int((hours * 60) / dt_minutes)

    for _ in range(steps):
        hour_of_day = current_time.hour + current_time.minute / 60.0
        state = twin.step(dt_seconds=dt_minutes * 60, hour_of_day=hour_of_day)
        yield {"timestamp": current_time, **state}
        current_time += timedelta(minutes=dt_minutes)


def comfort_pmv(room_temp_c: float, target_temp_c: float) -> float:
    """Approximate ASHRAE PMV (-3 cold .. 0 neutral .. +3 hot) from deviation off setpoint."""
    return round(max(-3.0, min(3.0, (room_temp_c - target_temp_c) / 1.5)), 2)


def predict_comfort_and_load(
    current_temp_c: float,
    target_temp_c: float,
    hour_of_day: float,
    horizon_minutes: float = 30,
    dt_minutes: float = 5,
) -> dict[str, Any]:
    """Project the twin forward from ``current_temp_c`` toward ``target_temp_c``.

    Used by the ``modelica_sim`` MCP tool: given a candidate setpoint, this
    answers "what would happen" -- the predicted comfort once the room
    settles, and the average HVAC load drawn getting there.
    """
    twin = HVACTwin(target_temp_c=target_temp_c, initial_temp_c=current_temp_c)
    steps = max(1, int(horizon_minutes / dt_minutes))
    power_samples_w = []

    hour = hour_of_day
    for _ in range(steps):
        state = twin.step(dt_seconds=dt_minutes * 60, hour_of_day=hour)
        power_samples_w.append(abs(state["hvac_power_w"]))
        hour = (hour + dt_minutes / 60.0) % 24

    avg_power_kw = (sum(power_samples_w) / len(power_samples_w)) / 1000.0
    return {
        "predicted_comfort_pmv": comfort_pmv(twin.current_temp_c, target_temp_c),
        "predicted_load_kw": round(avg_power_kw, 2),
    }


def run_simulation_and_export(output_filename: str = "hvac_simulation_data.xlsx") -> None:
    """Run a 24h simulation and export it to Excel -- a standalone CLI utility."""
    import pandas as pd

    print("Initializing HVAC Digital Twin...")
    start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    print("Running 24-hour simulation...")

    records = []
    for state in simulate_hours(hours=24, dt_minutes=5, start_time=start, target_temp_c=22.5):
        record = {"Timestamp": state["timestamp"].strftime("%Y-%m-%d %H:%M:%S")}
        record.update(
            {
                "Outside_Temp_C": state["outside_temp_c"],
                "Outside_Humidity_%": state["outside_humidity_pct"],
                "Room_Temp_C": state["room_temp_c"],
                "Room_Humidity_%": state["room_humidity_pct"],
                "HVAC_Status": state["hvac_status"],
                "Target_Temp_C": state["target_temp_c"],
            }
        )
        records.append(record)

    df = pd.DataFrame(records)
    try:
        df.to_excel(output_filename, index=False, engine="openpyxl")
        print(f"\nSimulation complete! Data saved to '{output_filename}'")
        print("\nPreview of the data:")
        print(df.head(10))
    except ImportError:
        print("\nError: 'openpyxl' is required to export to Excel.")
        print("Please install it by running: pip install openpyxl pandas")
    except Exception as exc:
        print(f"\nError saving Excel file: {exc}")


if __name__ == "__main__":
    run_simulation_and_export()
