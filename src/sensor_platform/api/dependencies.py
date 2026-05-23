"""Dependency injection — wires concrete adapters into FastAPI."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from sensor_platform.adapters.sqlite_metrics_store import SQLiteMetricsStore
from sensor_platform.adapters.sqlite_source import SQLiteDataSource
from sensor_platform.domain.schema import Schema
from sensor_platform.services.ingestion import IngestionService
from sensor_platform.services.metrics_service import MetricsService

_REPO_ROOT = Path(__file__).resolve().parents[3]

_SENSOR_DB = Path(os.environ.get("SENSOR_DB_PATH", str(_REPO_ROOT / "sensor_data.db")))
_METRICS_DB = Path(os.environ.get("METRICS_DB_PATH", str(_REPO_ROOT / "metrics.db")))
_SCHEMA_FILE = Path(os.environ.get("SCHEMA_PATH", str(_REPO_ROOT / "sensor_schema.json")))


@lru_cache
def get_schema() -> Schema:
    return Schema.from_file(_SCHEMA_FILE)


@lru_cache
def get_data_source() -> SQLiteDataSource:
    return SQLiteDataSource(_SENSOR_DB)


@lru_cache
def get_metrics_store() -> SQLiteMetricsStore:
    return SQLiteMetricsStore(_METRICS_DB)


@lru_cache
def get_ingestion_service() -> IngestionService:
    return IngestionService(get_data_source(), get_schema())


@lru_cache
def get_metrics_service() -> MetricsService:
    return MetricsService(get_ingestion_service(), get_metrics_store())
