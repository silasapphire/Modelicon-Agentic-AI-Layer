"""Database layer for the ModeliCon agentic BMS.

Two independent SQLite databases live here:

- ``database.building``: HVAC time-series / digital-twin data.
- ``database.memory``: persisted agent conversations and execution history.

Neither package imports from ``agents`` or ``graph`` — they are consumed
by the MCP tool layer, not the other way around.
"""
