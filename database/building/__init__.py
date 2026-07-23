"""Building data database package.

Stores HVAC digital-twin state: buildings, rooms, devices, time-series
sensor readings, and weather. The current data source is a temporary
HuggingFace dataset (see ``ingest_hf.py``); the schema itself makes no
assumption about that source so it can later be fed by a real Digital
Twin without migration.
"""
