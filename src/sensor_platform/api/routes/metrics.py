"""Metrics endpoints — process and query sensor metrics."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from sensor_platform.api.dependencies import get_metrics_service
from sensor_platform.api.schemas import (
    MetricResultSchema,
    ProcessRequest,
    ProcessResponse,
    QualityReportSchema,
    StationSchema,
)
from sensor_platform.services.metrics_service import MetricsService

router = APIRouter(prefix="/stations", tags=["metrics"])


@router.get("/", response_model=list[StationSchema])
def list_stations(svc: MetricsService = Depends(get_metrics_service)) -> list[StationSchema]:  # noqa: B008
    return [StationSchema(**s.__dict__) for s in svc.list_stations()]


@router.post("/{station_id}/process", response_model=ProcessResponse)
def process_station(
    station_id: str,
    req: ProcessRequest,
    svc: MetricsService = Depends(get_metrics_service),  # noqa: B008
) -> ProcessResponse:
    try:
        result = svc.process_station(
            station_id=station_id,
            resample_freq=req.resample_freq,
            start_time=req.start_time,
            end_time=req.end_time,
            missing_strategy=req.missing_strategy,
            metric_names=req.metric_names,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ProcessResponse(
        station_id=result.station_id,
        metrics=[MetricResultSchema(**m.__dict__) for m in result.metrics],
        quality_report=QualityReportSchema(
            total_rows=result.quality_report.total_rows,
            null_counts=result.quality_report.null_counts,
            out_of_range_counts=result.quality_report.out_of_range_counts,
            type_errors=result.quality_report.type_errors,
            flatline_count=len(result.quality_report.flatline_segments),
            quality_score=result.quality_report.quality_score,
        ),
        processed_at=result.processed_at,
    )


@router.get("/{station_id}/metrics", response_model=list[MetricResultSchema])
def get_metrics(
    station_id: str,
    device_id: str | None = None,
    metric_name: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    svc: MetricsService = Depends(get_metrics_service),  # noqa: B008
) -> list[MetricResultSchema]:
    results = svc.query_metrics(
        station_id=station_id,
        device_id=device_id,
        metric_name=metric_name,
        start_time=start_time,
        end_time=end_time,
    )
    return [MetricResultSchema(**r.__dict__) for r in results]
