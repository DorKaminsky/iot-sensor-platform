"""QualityReportStore protocol — abstract interface for persisting quality reports."""

from __future__ import annotations

from typing import Protocol

from sensor_platform.domain.models import QualityReport


class QualityReportStore(Protocol):
    def save(self, station_id: str, report: QualityReport) -> None:
        """Persist a quality report for a station (upsert — latest wins)."""
        ...

    def get(self, station_id: str) -> QualityReport | None:
        """Return the most recently stored quality report for a station, or None."""
        ...
