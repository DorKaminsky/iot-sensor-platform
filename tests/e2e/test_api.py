"""E2E tests for the FastAPI metrics endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sensor_platform.adapters.sqlite_metrics_store import SQLiteMetricsStore
from sensor_platform.adapters.sqlite_source import SQLiteDataSource
from sensor_platform.api.app import create_app
from sensor_platform.api.dependencies import (
    get_ingestion_service,
    get_metrics_service,
    get_metrics_store,
)
from sensor_platform.domain.schema import Schema
from sensor_platform.services.ingestion import IngestionService
from sensor_platform.services.metrics_service import MetricsService

_REPO = Path(__file__).resolve().parents[2]
STATION_ID = "d43f07f0-0170-5663-a459-04597edb38b6"


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    store = SQLiteMetricsStore(tmp_path / "metrics.db")
    source = SQLiteDataSource(_REPO / "sensor_data.db")
    schema = Schema.from_file(_REPO / "sensor_schema.json")
    ingestion = IngestionService(source, schema)
    svc = MetricsService(ingestion, store)

    app = create_app()
    app.dependency_overrides[get_metrics_store] = lambda: store
    app.dependency_overrides[get_ingestion_service] = lambda: ingestion
    app.dependency_overrides[get_metrics_service] = lambda: svc

    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestProcessEndpoint:
    def test_process_returns_metrics(self, client: TestClient) -> None:
        resp = client.post(
            f"/stations/{STATION_ID}/process",
            json={
                "resample_freq": "1h",
                "start_time": "2024-02-01T00:00:00Z",
                "end_time": "2024-02-02T00:00:00Z",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["station_id"] == STATION_ID
        assert len(body["metrics"]) > 0
        assert "quality_report" in body
        assert body["quality_report"]["total_rows"] > 0

    def test_process_includes_uptime_metric(self, client: TestClient) -> None:
        resp = client.post(
            f"/stations/{STATION_ID}/process",
            json={"resample_freq": "1h"},
        )
        assert resp.status_code == 200
        names = [m["metric_name"] for m in resp.json()["metrics"]]
        assert "uptime_pct" in names

    def test_invalid_station_returns_empty_metrics(self, client: TestClient) -> None:
        resp = client.post(
            "/stations/nonexistent-station/process",
            json={"resample_freq": "1h"},
        )
        assert resp.status_code == 200
        assert resp.json()["metrics"] == []


class TestGetMetricsEndpoint:
    def test_query_before_process_returns_404(self, client: TestClient) -> None:
        resp = client.get(f"/stations/{STATION_ID}/metrics")
        assert resp.status_code == 404
        assert "Run POST" in resp.json()["detail"]
        client.post(
            f"/stations/{STATION_ID}/process",
            json={
                "resample_freq": "1h",
                "start_time": "2024-02-01T00:00:00Z",
                "end_time": "2024-02-02T00:00:00Z",
            },
        )
        resp = client.get(f"/stations/{STATION_ID}/metrics")
        assert resp.status_code == 200
        assert len(resp.json()) > 0

    def test_filter_by_metric_name(self, client: TestClient) -> None:
        client.post(
            f"/stations/{STATION_ID}/process",
            json={"resample_freq": "1h"},
        )
        resp = client.get(
            f"/stations/{STATION_ID}/metrics",
            params={"metric_name": "avg_pressure"},
        )
        assert resp.status_code == 200
        assert all(m["metric_name"] == "avg_pressure" for m in resp.json())
