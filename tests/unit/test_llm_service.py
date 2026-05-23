"""Unit tests for LLMService — mocks the LLMClient port."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sensor_platform.domain.exceptions import LLMError
from sensor_platform.domain.models import MetricResult
from sensor_platform.services.llm_service import LLMService, _strip_markdown


def _metric(name: str, value: float, device: str = "dev-A") -> MetricResult:
    t = datetime(2024, 2, 1, tzinfo=UTC)
    return MetricResult(
        metric_name=name,
        station_id="s1",
        device_id=device,
        value=value,
        start_time=t,
        end_time=t,
        resample_freq="5min",
        missing_strategy="drop",
    )


class _MockLLMClient:
    def __init__(self, response: str = "mock summary", raises: Exception | None = None) -> None:
        self.response = response
        self.raises = raises
        self.calls: list[tuple[str, str]] = []

    def generate(self, system: str, user: str, max_tokens: int = 2048) -> str:
        self.calls.append((system, user))
        if self.raises:
            raise self.raises
        return self.response


class TestSummarizeHealth:
    def test_returns_llm_response(self) -> None:
        mock = _MockLLMClient("All systems nominal.")
        svc = LLMService(mock)
        result = svc.summarize_health("s1", [_metric("uptime_pct", 95.0)])
        assert result == "All systems nominal."

    def test_calls_llm_once(self) -> None:
        mock = _MockLLMClient()
        svc = LLMService(mock)
        svc.summarize_health("s1", [_metric("uptime_pct", 95.0)])
        assert len(mock.calls) == 1

    def test_prompt_contains_station_id(self) -> None:
        mock = _MockLLMClient()
        svc = LLMService(mock)
        svc.summarize_health("my-station-42", [_metric("uptime_pct", 95.0)])
        _, user = mock.calls[0]
        assert "my-station-42" in user

    def test_prompt_contains_metric_name_and_value(self) -> None:
        mock = _MockLLMClient()
        svc = LLMService(mock)
        svc.summarize_health("s1", [_metric("avg_pressure", 8.25)])
        _, user = mock.calls[0]
        assert "avg_pressure" in user
        assert "8.25" in user

    def test_prompt_contains_device_id(self) -> None:
        mock = _MockLLMClient()
        svc = LLMService(mock)
        svc.summarize_health("s1", [_metric("uptime_pct", 95.0, device="compressor-3")])
        _, user = mock.calls[0]
        assert "compressor-3" in user

    def test_system_prompt_is_non_empty(self) -> None:
        mock = _MockLLMClient()
        svc = LLMService(mock)
        svc.summarize_health("s1", [_metric("uptime_pct", 95.0)])
        system, _ = mock.calls[0]
        assert len(system) > 10

    def test_propagates_llm_error(self) -> None:
        mock = _MockLLMClient(raises=LLMError("API down"))
        svc = LLMService(mock)
        with pytest.raises(LLMError, match="API down"):
            svc.summarize_health("s1", [_metric("uptime_pct", 95.0)])

    def test_multiple_metrics_all_appear_in_prompt(self) -> None:
        mock = _MockLLMClient()
        svc = LLMService(mock)
        svc.summarize_health(
            "s1",
            [
                _metric("uptime_pct", 95.0),
                _metric("avg_pressure", 8.1),
                _metric("specific_power", 0.5),
            ],
        )
        _, user = mock.calls[0]
        assert "uptime_pct" in user
        assert "avg_pressure" in user
        assert "specific_power" in user

    def test_markdown_stripped_from_response(self) -> None:
        mock = _MockLLMClient("**Station** is _healthy_. Uptime at `95%`.")
        svc = LLMService(mock)
        result = svc.summarize_health("s1", [_metric("uptime_pct", 95.0)])
        assert "**" not in result
        assert "_" not in result
        assert "`" not in result
        assert "Station" in result
        assert "healthy" in result


class TestStripMarkdown:
    def test_removes_bold(self) -> None:
        assert _strip_markdown("**bold**") == "bold"

    def test_removes_italic(self) -> None:
        assert _strip_markdown("*italic*") == "italic"

    def test_removes_underscore_bold(self) -> None:
        assert _strip_markdown("__bold__") == "bold"

    def test_removes_underscore_italic(self) -> None:
        assert _strip_markdown("_italic_") == "italic"

    def test_removes_headers(self) -> None:
        assert _strip_markdown("## Title\nBody text.") == "Title\nBody text."

    def test_removes_inline_code(self) -> None:
        assert _strip_markdown("`code`") == "code"

    def test_removes_bullet_points(self) -> None:
        result = _strip_markdown("- item one\n- item two")
        assert "-" not in result
        assert "item one" in result
        assert "item two" in result

    def test_collapses_extra_blank_lines(self) -> None:
        result = _strip_markdown("line1\n\n\n\nline2")
        assert "\n\n\n" not in result

    def test_plain_text_unchanged(self) -> None:
        text = "Station is running at 95% uptime with stable pressure."
        assert _strip_markdown(text) == text

    def test_strips_leading_trailing_whitespace(self) -> None:
        assert _strip_markdown("  hello  ") == "hello"
