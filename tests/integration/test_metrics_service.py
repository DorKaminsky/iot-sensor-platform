"""Integration tests for MetricsService end-to-end."""

from __future__ import annotations

from datetime import UTC, datetime

from sensor_platform.services.metrics_service import MetricsService

STATION_ID = "d43f07f0-0170-5663-a459-04597edb38b6"
START = datetime(2024, 2, 1, tzinfo=UTC)
END = datetime(2024, 2, 2, tzinfo=UTC)


class TestMetricsService:
    def test_process_station_returns_metrics(self, metrics_service: MetricsService) -> None:
        result = metrics_service.process_station(
            station_id=STATION_ID,
            resample_freq="1h",
            start_time=START,
            end_time=END,
        )
        assert len(result.metrics) > 0
        names = {m.metric_name for m in result.metrics}
        assert "uptime_pct" in names
        assert "avg_pressure" in names

    def test_metrics_are_persisted_and_queryable(self, metrics_service: MetricsService) -> None:
        metrics_service.process_station(
            station_id=STATION_ID,
            resample_freq="1h",
            start_time=START,
            end_time=END,
        )
        stored = metrics_service.query_metrics(station_id=STATION_ID)
        assert len(stored) > 0
        assert all(m.station_id == STATION_ID for m in stored)

    def test_uptime_pct_in_valid_range(self, metrics_service: MetricsService) -> None:
        result = metrics_service.process_station(
            station_id=STATION_ID,
            resample_freq="1h",
            start_time=START,
            end_time=END,
        )
        for m in result.metrics:
            if m.metric_name == "uptime_pct":
                assert 0.0 <= m.value <= 100.0

    def test_query_filter_by_metric_name(self, metrics_service: MetricsService) -> None:
        metrics_service.process_station(
            station_id=STATION_ID,
            resample_freq="1h",
            start_time=START,
            end_time=END,
        )
        results = metrics_service.query_metrics(station_id=STATION_ID, metric_name="avg_pressure")
        assert all(m.metric_name == "avg_pressure" for m in results)

    def test_process_station_includes_quality_report(self, metrics_service: MetricsService) -> None:
        result = metrics_service.process_station(
            station_id=STATION_ID,
            resample_freq="1h",
            start_time=START,
            end_time=END,
        )
        assert result.quality_report.total_rows > 0
        assert 0 <= result.quality_report.quality_score <= 100
