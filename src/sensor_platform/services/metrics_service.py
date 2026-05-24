"""MetricsService — orchestrates ingestion, metric computation, and storage."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from sensor_platform.domain import metrics as metric_fns
from sensor_platform.domain.models import (
    MetricResult,
    MissingStrategy,
    ProcessingResult,
    QualityReport,
    Station,
)
from sensor_platform.ports.metrics_store import MetricsStore
from sensor_platform.ports.quality_report_store import QualityReportStore
from sensor_platform.services.ingestion import IngestionService

_DEFAULT_METRICS = [
    "uptime_pct",
    "avg_pressure",
    "peak_pressure",
    "specific_power",
    "cycle_count",
]


class MetricsService:
    def __init__(
        self,
        ingestion: IngestionService,
        store: MetricsStore,
        quality_store: QualityReportStore | None = None,
    ) -> None:
        self._ingestion = ingestion
        self._store = store
        self._quality_store = quality_store

    def process_station(
        self,
        station_id: str,
        resample_freq: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        missing_strategy: MissingStrategy = "drop",
        metric_names: list[str] | None = None,
    ) -> ProcessingResult:
        """Ingest, compute, store, and return metrics + quality report."""
        names = metric_names or _DEFAULT_METRICS

        df, quality_report = self._ingestion.ingest(
            resample_freq=resample_freq,
            station_id=station_id,
            start_time=start_time,
            end_time=end_time,
            missing_strategy=missing_strategy,
        )

        results: list[MetricResult] = []
        _now = datetime.now(UTC)
        t_start = start_time or (df["timestamp"].min().to_pydatetime() if not df.empty else _now)
        t_end = end_time or (df["timestamp"].max().to_pydatetime() if not df.empty else _now)

        freq_minutes = _freq_to_minutes(resample_freq)

        for device_id, device_df in df.groupby("device_id"):
            for name in names:
                value = _compute(name, device_df, freq_minutes)
                if value is None:
                    continue
                results.append(
                    MetricResult(
                        metric_name=name,
                        station_id=station_id,
                        device_id=str(device_id),
                        value=value,
                        start_time=t_start,
                        end_time=t_end,
                        resample_freq=resample_freq,
                        missing_strategy=missing_strategy,
                    )
                )

        if results:
            self._store.save(results)

        if self._quality_store is not None:
            self._quality_store.save(station_id, quality_report)

        return ProcessingResult(
            station_id=station_id,
            metrics=results,
            quality_report=quality_report,
        )

    def query_metrics(
        self,
        station_id: str | None = None,
        device_id: str | None = None,
        metric_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[MetricResult]:
        return self._store.query(
            station_id=station_id,
            device_id=device_id,
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
        )

    def get_quality_report(self, station_id: str) -> QualityReport | None:
        """Return the stored quality report for a station, or None if not yet processed."""
        if self._quality_store is None:
            return None
        return self._quality_store.get(station_id)

    def list_stations(self) -> list[Station]:
        return self._ingestion._source.read_stations()

    def process_all_stations(
        self,
        resample_freq: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        missing_strategy: MissingStrategy = "drop",
        metric_names: list[str] | None = None,
    ) -> list[ProcessingResult]:
        return [
            self.process_station(
                station_id=station.station_id,
                resample_freq=resample_freq,
                start_time=start_time,
                end_time=end_time,
                missing_strategy=missing_strategy,
                metric_names=metric_names,
            )
            for station in self.list_stations()
        ]


def _compute(name: str, df: pd.DataFrame, freq_minutes: float) -> float | None:
    if name == "total_flow_volume":
        return metric_fns.compute_total_flow_volume(df, freq_minutes)
    fn = metric_fns.METRIC_REGISTRY.get(name)
    if fn is None:
        return None
    return fn(df)


def _freq_to_minutes(freq: str) -> float:
    """Convert pandas frequency string to minutes (best-effort for common values)."""
    try:
        td = pd.tseries.frequencies.to_offset(freq)
        if td is not None:
            return td.nanos / 1e9 / 60
    except Exception:
        pass
    return 1.0
