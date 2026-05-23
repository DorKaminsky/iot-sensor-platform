"""Prompt templates — pure functions, no I/O, independently testable."""

from __future__ import annotations

from sensor_platform.domain.models import MetricResult


def health_summary_prompt(station_id: str, metrics: list[MetricResult]) -> tuple[str, str]:
    """Return (system, user) prompts for a station health summary."""
    system = (
        "You are an industrial IoT analyst summarising compressor station health. "
        "Be concise (2-3 sentences). Focus on uptime, pressure stability, efficiency "
        "(specific power), and cycle patterns. Use plain language for operators. "
        "Respond with plain text only — no markdown, no bullet points, no headers."
    )
    lines = "\n".join(
        f"  {m.device_id} | {m.metric_name}: {m.value:.2f}" for m in metrics
    )
    user = f"Station {station_id} metrics:\n{lines}\n\nProvide a health summary."
    return system, user
