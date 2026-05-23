"""Prompt templates — pure functions, no I/O, independently testable."""

from __future__ import annotations

from sensor_platform.domain.models import MetricResult, QualityReport


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


def quality_report_prompt(station_id: str, report: QualityReport) -> tuple[str, str]:
    """Return (system, user) prompts for a station data quality summary."""
    system = (
        "You are an industrial IoT data quality analyst. "
        "Summarise the data quality of a compressor station in 2-3 sentences. "
        "Highlight the most significant issues: missing data, out-of-range sensor readings, "
        "and sensor flatlines. Use plain language for operators. "
        "Respond with plain text only — no markdown, no bullet points, no headers."
    )
    null_lines = "\n".join(
        f"  {col}: {count} nulls ({report.null_pct.get(col, 0):.1f}%)"
        for col, count in report.null_counts.items()
        if count > 0
    ) or "  None"
    oob_lines = "\n".join(
        f"  {col}: {count} out-of-range readings"
        for col, count in report.out_of_range_counts.items()
        if count > 0
    ) or "  None"
    user = (
        f"Station {station_id} data quality report:\n"
        f"Total rows: {report.total_rows}\n"
        f"Quality score: {report.quality_score:.1f}/100\n"
        f"Missing values:\n{null_lines}\n"
        f"Out-of-range readings:\n{oob_lines}\n"
        f"Flatline segments: {len(report.flatline_segments)}\n"
        f"\nProvide a data quality summary."
    )
    return system, user
