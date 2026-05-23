"""LLM-powered analysis endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from sensor_platform.api.dependencies import get_llm_service, get_metrics_service
from sensor_platform.api.schemas import SummaryResponse
from sensor_platform.domain.exceptions import LLMError
from sensor_platform.services.llm_service import LLMService
from sensor_platform.services.metrics_service import MetricsService

router = APIRouter(prefix="/stations", tags=["llm"])


@router.post("/{station_id}/summarize", response_model=SummaryResponse)
def summarize_health(
    station_id: str,
    llm: LLMService = Depends(get_llm_service),  # noqa: B008
    metrics_svc: MetricsService = Depends(get_metrics_service),  # noqa: B008
) -> SummaryResponse:
    """Generate a plain-English health summary from the station's stored metrics."""
    metrics = metrics_svc.query_metrics(station_id=station_id)
    if not metrics:
        raise HTTPException(
            status_code=404,
            detail=f"No metrics found for station {station_id!r}. Run /process first.",
        )
    try:
        summary = llm.summarize_health(station_id, metrics)
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=f"LLM unavailable: {exc}") from exc
    return SummaryResponse(station_id=station_id, summary=summary)
