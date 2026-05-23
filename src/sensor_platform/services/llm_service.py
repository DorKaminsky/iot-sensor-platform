"""LLMService — orchestrates prompt construction and LLM generation."""

from __future__ import annotations

import re

from sensor_platform.domain.models import MetricResult, QualityReport
from sensor_platform.domain.prompts import (
    health_summary_prompt,
    quality_report_prompt,
    query_prompt,
)
from sensor_platform.ports.llm_client import LLMClient


def _strip_markdown(text: str) -> str:
    """Remove common markdown syntax so responses are plain readable text."""
    # Headers: ## Title → Title
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Bold/italic: **text**, *text*, __text__, _text_
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", text)
    # Inline code: `text`
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Bullet points: leading "- " or "* "
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)
    # Collapse multiple blank lines into one
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class LLMService:
    def __init__(self, llm_client: LLMClient) -> None:
        self._client = llm_client

    def summarize_health(self, station_id: str, metrics: list[MetricResult]) -> str:
        """Generate plain-English health summary from stored metrics."""
        system, user = health_summary_prompt(station_id, metrics)
        raw = self._client.generate(system, user, max_tokens=512)
        return _strip_markdown(raw)

    def summarize_quality(self, station_id: str, report: QualityReport) -> str:
        """Generate plain-English data quality summary from a stored quality report."""
        system, user = quality_report_prompt(station_id, report)
        raw = self._client.generate(system, user, max_tokens=512)
        return _strip_markdown(raw)

    def answer_query(self, station_id: str, metrics: list[MetricResult], question: str) -> str:
        """Answer a free-text question about a station using its stored metrics as context."""
        system, user = query_prompt(station_id, metrics, question)
        raw = self._client.generate(system, user, max_tokens=512)
        return _strip_markdown(raw)
