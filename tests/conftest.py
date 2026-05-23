"""Shared pytest fixtures."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from sensor_platform.adapters.sqlite_metrics_store import SQLiteMetricsStore
from sensor_platform.adapters.sqlite_source import SQLiteDataSource
from sensor_platform.domain.schema import Schema
from sensor_platform.services.ingestion import IngestionService
from sensor_platform.services.metrics_service import MetricsService

_REPO_ROOT = Path(__file__).resolve().parents[1]
SENSOR_DB = _REPO_ROOT / "sensor_data.db"
SCHEMA_FILE = _REPO_ROOT / "sensor_schema.json"


@pytest.fixture
def schema() -> Schema:
    return Schema.from_file(SCHEMA_FILE)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """30 rows of synthetic sensor data — 2 devices, known patterns."""
    rows = []
    base = datetime(2024, 2, 1, tzinfo=UTC)
    for i in range(15):
        ts = base.replace(minute=i)
        for dev in ("dev-A", "dev-B"):
            rows.append(
                {
                    "timestamp": ts,
                    "station_id": "station-1",
                    "device_id": dev,
                    "discharge_pressure": 8.0 + i * 0.1,
                    "air_flow_rate": 100.0 + i,
                    "power_consumption": 50.0 + i * 0.5,
                    "motor_speed": 1500 + i * 10 if i > 0 else 0,
                    "discharge_temp": 60.0,
                }
            )
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


@pytest.fixture
def sample_df_with_nulls(sample_df: pd.DataFrame) -> pd.DataFrame:
    df = sample_df.copy()
    df.loc[df.index[:4], "discharge_pressure"] = None
    df.loc[df.index[10:12], "air_flow_rate"] = None
    return df


@pytest.fixture
def metrics_store(tmp_path: Path) -> SQLiteMetricsStore:
    return SQLiteMetricsStore(tmp_path / "metrics.db")


@pytest.fixture
def sqlite_source() -> SQLiteDataSource:
    return SQLiteDataSource(SENSOR_DB)


@pytest.fixture
def ingestion_service(sqlite_source: SQLiteDataSource, schema: Schema) -> IngestionService:
    return IngestionService(sqlite_source, schema)


@pytest.fixture
def metrics_service(
    ingestion_service: IngestionService,
    metrics_store: SQLiteMetricsStore,
) -> MetricsService:
    return MetricsService(ingestion_service, metrics_store)
