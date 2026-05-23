"""E2E tests for LLM endpoints — mock the LLM client, use real metrics store."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sensor_platform.adapters.sqlite_metrics_store import SQLiteMetricsStore
from sensor_platform.adapters.sqlite_source import SQLiteDataSource
from sensor_platform.api.app import create_app
from sensor_platform.api.dependencies import (
    get_ingestion_service,
    get_llm_service,
    get_metrics_service,
    get_metrics_store,
)
from sensor_platform.domain.schema import Schema
from sensor_platform.services.ingestion import IngestionService
from sensor_platform.services.llm_service import LLMService
from sensor_platform.services.metrics_service import MetricsService

_REPO = Path(__file__).resolve().parents[2]
STATION_ID = "d43f07f0-0170-5663-a459-04597edb38b6"


class _StubLLMClient:
    def generate(self, system: str, user: str, max_tokens: int = 2048) -> str:
        return "Station is running at 92% uptime with stable pressure."


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    store = SQLiteMetricsStore(tmp_path / "metrics.db")
    source = SQLiteDataSource(_REPO / "sensor_data.db")
    schema = Schema.from_file(_REPO / "sensor_schema.json")
    ingestion = IngestionService(source, schema)
    svc = MetricsService(ingestion, store)
    llm_svc = LLMService(_StubLLMClient())  # type: ignore[arg-type]

    app = create_app()
    app.dependency_overrides[get_metrics_store] = lambda: store
    app.dependency_overrides[get_ingestion_service] = lambda: ingestion
    app.dependency_overrides[get_metrics_service] = lambda: svc
    app.dependency_overrides[get_llm_service] = lambda: llm_svc

    return TestClient(app)


class TestSummarizeEndpoint:
    def test_404_when_no_metrics_processed(self, client: TestClient) -> None:
        resp = client.post(f"/stations/{STATION_ID}/summarize")
        assert resp.status_code == 404
        assert "No metrics found" in resp.json()["detail"]

    def test_returns_summary_after_process(self, client: TestClient) -> None:
        client.post(
            f"/stations/{STATION_ID}/process",
            json={
                "resample_freq": "1h",
                "start_time": "2024-02-01T00:00:00Z",
                "end_time": "2024-02-02T00:00:00Z",
            },
        )
        resp = client.post(f"/stations/{STATION_ID}/summarize")
        assert resp.status_code == 200
        body = resp.json()
        assert body["station_id"] == STATION_ID
        assert len(body["summary"]) > 10

    def test_summary_comes_from_llm(self, client: TestClient) -> None:
        client.post(
            f"/stations/{STATION_ID}/process",
            json={"resample_freq": "1h"},
        )
        resp = client.post(f"/stations/{STATION_ID}/summarize")
        assert resp.status_code == 200
        assert resp.json()["summary"] == "Station is running at 92% uptime with stable pressure."

    def test_503_when_llm_raises(self, tmp_path: Path) -> None:
        from sensor_platform.domain.exceptions import LLMError

        store = SQLiteMetricsStore(tmp_path / "metrics.db")
        source = SQLiteDataSource(_REPO / "sensor_data.db")
        schema = Schema.from_file(_REPO / "sensor_schema.json")
        ingestion = IngestionService(source, schema)
        svc = MetricsService(ingestion, store)

        class _FailingLLM:
            def generate(self, system: str, user: str, max_tokens: int = 2048) -> str:
                raise LLMError("LLM is down")

        llm_svc = LLMService(_FailingLLM())  # type: ignore[arg-type]

        app = create_app()
        app.dependency_overrides[get_metrics_store] = lambda: store
        app.dependency_overrides[get_ingestion_service] = lambda: ingestion
        app.dependency_overrides[get_metrics_service] = lambda: svc
        app.dependency_overrides[get_llm_service] = lambda: llm_svc

        c = TestClient(app)
        c.post(
            f"/stations/{STATION_ID}/process",
            json={"resample_freq": "1h"},
        )
        resp = c.post(f"/stations/{STATION_ID}/summarize")
        assert resp.status_code == 503
        assert "LLM unavailable" in resp.json()["detail"]
