"""Domain models — core data contracts, no I/O dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

MissingStrategy = Literal["drop", "fill", "interpolate", "ffill"]

SENSOR_COLUMNS = [
    "discharge_pressure",
    "air_flow_rate",
    "power_consumption",
    "motor_speed",
    "discharge_temp",
]


@dataclass(frozen=True)
class Station:
    station_id: str
    station_name: str
    location: str
    commissioned_date: str
    num_compressors: int


@dataclass(frozen=True)
class FlatlineSegment:
    device_id: str
    sensor: str
    start_time: datetime
    end_time: datetime
    duration_minutes: float
    value: float


@dataclass
class QualityReport:
    total_rows: int
    null_counts: dict[str, int]
    out_of_range_counts: dict[str, int]
    flatline_segments: list[FlatlineSegment]
    type_errors: dict[str, int] = field(default_factory=dict)

    @property
    def null_pct(self) -> dict[str, float]:
        if self.total_rows == 0:
            return {col: 0.0 for col in self.null_counts}
        return {col: count / self.total_rows * 100 for col, count in self.null_counts.items()}

    @property
    def quality_score(self) -> float:
        """0–100: 100 = perfect data, penalises nulls, out-of-range, type errors, and flatlines."""
        if self.total_rows == 0:
            return 0.0
        total_issues = (
            sum(self.null_counts.values())
            + sum(self.out_of_range_counts.values())
            + sum(self.type_errors.values())
        )
        issue_rate = total_issues / (self.total_rows * len(SENSOR_COLUMNS))
        flatline_penalty = min(len(self.flatline_segments) * 2, 20)
        return max(0.0, round((1 - issue_rate) * 100 - flatline_penalty, 1))


@dataclass(frozen=True)
class MetricResult:
    metric_name: str
    station_id: str
    device_id: str
    value: float
    start_time: datetime
    end_time: datetime
    resample_freq: str
    missing_strategy: MissingStrategy


@dataclass
class ProcessingResult:
    station_id: str
    metrics: list[MetricResult]
    quality_report: QualityReport
    processed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
