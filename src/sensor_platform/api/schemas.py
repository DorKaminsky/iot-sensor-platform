"""Pydantic request/response schemas for the API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from sensor_platform.domain.models import MissingStrategy


class ProcessRequest(BaseModel):
    resample_freq: str = Field(
        ..., examples=["5min", "1h"], description="Pandas-compatible frequency string"
    )
    start_time: datetime | None = None
    end_time: datetime | None = None
    missing_strategy: MissingStrategy = "drop"
    metric_names: list[str] | None = None


class MetricResultSchema(BaseModel):
    metric_name: str
    station_id: str
    device_id: str
    value: float
    start_time: datetime
    end_time: datetime
    resample_freq: str
    missing_strategy: str


class QualityReportSchema(BaseModel):
    total_rows: int
    null_counts: dict[str, int]
    out_of_range_counts: dict[str, int]
    type_errors: dict[str, int]
    flatline_count: int
    quality_score: float


class ProcessResponse(BaseModel):
    station_id: str
    metrics: list[MetricResultSchema]
    quality_report: QualityReportSchema
    processed_at: datetime


class StationSchema(BaseModel):
    station_id: str
    station_name: str
    location: str
    commissioned_date: str
    num_compressors: int


class SummaryResponse(BaseModel):
    station_id: str
    summary: str


class QualityReportSummaryResponse(BaseModel):
    station_id: str
    quality_score: float
    summary: str


class QueryRequest(BaseModel):
    question: str = Field(..., description="Free-text question about the station's metrics")


class QueryResponse(BaseModel):
    station_id: str
    question: str
    answer: str
