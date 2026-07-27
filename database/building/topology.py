"""Static building topology: 1 building, 3 floors, 3 rooms per floor.

This module does no I/O and touches no database -- it is the single
source of truth for "what rooms exist" that both the seeding script
(``seed_topology.py``) and the live pipeline (MCP server, agents,
guardrail) import, so a room name is validated/interpreted the same way
everywhere.
"""

from __future__ import annotations

BUILDING_NAME = "Default Building"
FLOORS: tuple[int, ...] = (1, 2, 3)
ROOMS_PER_FLOOR = 3

#: One entry per room: floor number, canonical room name, HVAC device name.
ROOM_ROSTER: tuple[dict[str, object], ...] = tuple(
    {
        "floor": floor,
        "room_name": f"Floor {floor} Room {room}",
        "device_name": f"AHU-F{floor}R{room}",
    }
    for floor in FLOORS
    for room in range(1, ROOMS_PER_FLOOR + 1)
)

ROOM_NAMES: tuple[str, ...] = tuple(r["room_name"] for r in ROOM_ROSTER)

#: Sentinel used when a request applies to the whole building rather than
#: one specific room (e.g. "what's the average temperature?").
BUILDING_WIDE = "building-wide"


def is_known_room(name: str | None) -> bool:
    return name in ROOM_NAMES


def rooms_by_floor(floor: int) -> tuple[str, ...]:
    return tuple(r["room_name"] for r in ROOM_ROSTER if r["floor"] == floor)


def topology_summary() -> dict:
    """Building structure in a shape safe to hand straight to an LLM or a tool caller."""
    return {
        "building_name": BUILDING_NAME,
        "floors": list(FLOORS),
        "rooms_by_floor": {floor: list(rooms_by_floor(floor)) for floor in FLOORS},
        "all_rooms": list(ROOM_NAMES),
    }
