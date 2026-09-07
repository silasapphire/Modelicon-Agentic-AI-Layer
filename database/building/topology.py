"""Static building topology: a single HVAC zone.

This used to describe a synthetic 3-floor, 9-room building. It now
matches the OpenModelica digital twin at ``Building_1/HVAC.mo``, which
models exactly one zone -- so the building is one room, not nine. This
module still does no I/O; it's the single source of truth for "what
room(s) exist" that the MCP server, agents, and guardrail import, so a
room name is validated/interpreted the same way everywhere.
"""

from __future__ import annotations

BUILDING_NAME = "Default Building"

#: The one zone the digital twin models.
ZONE_NAME = "Zone 1"
DEVICE_NAME = "AHU-Zone1"

#: Every room name the building recognises. Kept as a tuple (rather than
#: just ZONE_NAME) so code that iterates "every room" -- the non-thermal
#: domain tools in mcp_server/server.py -- doesn't need special-casing
#: for a single-zone building; it just iterates a 1-element tuple.
ROOM_NAMES: tuple[str, ...] = (ZONE_NAME,)

#: Sentinel used when a request applies to the whole building rather
#: than the one specific zone by name -- both mean the same physical
#: space here, but callers (agents) use this when no room was named.
BUILDING_WIDE = "building-wide"


def is_known_room(name: str | None) -> bool:
    return name in ROOM_NAMES


def topology_summary() -> dict:
    """Building structure in a shape safe to hand straight to an LLM or a tool caller."""
    return {
        "building_name": BUILDING_NAME,
        "zones": list(ROOM_NAMES),
        "note": "single-zone building, modeled by an OpenModelica FMU digital twin",
    }
