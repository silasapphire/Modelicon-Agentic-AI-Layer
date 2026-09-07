"""Building data database package.

Stores HVAC digital-twin state: buildings, rooms, devices, time-series
sensor readings, and weather. Readings are sourced from the OpenModelica
FMU digital twin (see ``ingest_fmu.py``); the schema itself makes no
assumption about that source, so it could be fed by a different twin
later without migration.
"""
