# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A take-home assignment starter kit for building an industrial IoT data platform in Python. The repository currently contains only the provided assets — **no implementation exists yet**. The assignment requires building from scratch.

**Provided assets (do not modify):**
- `sensor_data.db` — SQLite database with 30 days of compressor sensor data (tables: `sensor_readings`, `station_metadata`)
- `sensor_schema.json` — Schema with column types, valid ranges, and flatline thresholds per sensor
- `producer.py` — Event producer for Challenge 3; publishes `SensorEvent` dicts into a `queue.Queue`, ends stream with `None` sentinel

## Assignment Scope

**Challenge 1 (required):** Reusable ingestion library + FastAPI metrics service + tests + design doc  
**Challenge 2 (optional):** LLM-powered endpoint on top of Challenge 1  
**Challenge 3 (optional):** Event-driven consumer for the `producer.py` queue  

## Database Schema

**`sensor_readings`:** `timestamp`, `station_id`, `device_id`, `discharge_pressure` (bar, 0–16), `air_flow_rate` (m³/h, 0–600), `power_consumption` (kW, 0–350), `motor_speed` (RPM int, 0–4000), `discharge_temp` (°C, -10–120)

**`station_metadata`:** `station_id`, `station_name`, `location`, `commissioned_date`, `num_compressors`

**Data quality issues in the DB:** missing values, gaps, sensor flatlines, noisy readings.

## Producer Contract (Challenge 3)

```python
from producer import SensorEventProducer
import queue

q = queue.Queue()
producer = SensorEventProducer(db_path="sensor_data.db", event_queue=q)
producer.start()
# stream ends with None sentinel
```

`SensorEvent` fields: `event_id`, `event_type`, `timestamp` (ISO 8601), `station_id`, `device_id`, `readings` (dict of sensor→float|int|None), `metadata`. Producer injects ~2% malformed events by default.

## Intended Architecture

The library must be **framework-agnostic** with an abstract data access layer so the backing store (SQLite → BigQuery) can be swapped without changing consumers. The API service is a thin wrapper over the library. For Challenge 3, the queue transport must be swappable (in-memory → Redis Streams/Pub/Sub) without changing processing logic.

## Python Version

Python 3.11+ required (per `take-home-README.txt`).
