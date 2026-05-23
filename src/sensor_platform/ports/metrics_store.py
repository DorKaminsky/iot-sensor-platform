"""MetricsStore protocol — abstract interface for persisting computed metrics."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from sensor_platform.domain.models import MetricResult


class MetricsStore(Protocol):
    def save(self, results: list[MetricResult]) -> None:
        """Persist computed metric results (upsert by natural key)."""
        ...

    def query(
        self,
        station_id: str | None = None,
        device_id: str | None = None,
        metric_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[MetricResult]:
        """Return stored metrics matching the given filters."""
        ...
