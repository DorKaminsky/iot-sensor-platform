"""Integration tests for LLM adapters — mock HTTP/SDK, verify retry and error handling."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from sensor_platform.adapters.claude_adapter import ClaudeAdapter
from sensor_platform.adapters.ollama_adapter import OllamaAdapter
from sensor_platform.domain.exceptions import LLMError


class TestClaudeAdapter:
    def _mock_response(self, text: str) -> MagicMock:
        block = MagicMock()
        block.text = text
        resp = MagicMock()
        resp.content = [block]
        return resp

    def test_client_has_explicit_timeout(self) -> None:
        adapter = ClaudeAdapter(api_key="test-key")
        assert adapter._client.timeout == 30.0

    def test_returns_text_on_success(self) -> None:
        with patch("sensor_platform.adapters.claude_adapter.anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = self._mock_response("hello")
            adapter = ClaudeAdapter(api_key="test-key")
            assert adapter.generate("sys", "usr") == "hello"

    def test_raises_llm_error_on_api_error(self) -> None:
        import anthropic

        with patch("sensor_platform.adapters.claude_adapter.anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.side_effect = anthropic.APIStatusError(
                "bad request",
                response=MagicMock(status_code=400),
                body={},
            )
            adapter = ClaudeAdapter(api_key="test-key")
            with pytest.raises(LLMError, match="Claude API error"):
                adapter.generate("sys", "usr")

    def test_retries_on_timeout_then_succeeds(self) -> None:
        import anthropic

        with patch("sensor_platform.adapters.claude_adapter.anthropic.Anthropic") as mock_cls:
            create = mock_cls.return_value.messages.create
            create.side_effect = [
                anthropic.APITimeoutError(request=MagicMock()),
                self._mock_response("recovered"),
            ]
            adapter = ClaudeAdapter(api_key="test-key")
            result = adapter.generate("sys", "usr")
            assert result == "recovered"
            assert create.call_count == 2

    def test_raises_after_all_retries_exhausted(self) -> None:
        import anthropic

        with patch("sensor_platform.adapters.claude_adapter.anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.side_effect = anthropic.APITimeoutError(
                request=MagicMock()
            )
            adapter = ClaudeAdapter(api_key="test-key")
            with pytest.raises(anthropic.APITimeoutError):
                adapter.generate("sys", "usr")
            assert mock_cls.return_value.messages.create.call_count == 3


class TestOllamaAdapter:
    def _mock_httpx(self, json_body: dict) -> MagicMock:
        resp = MagicMock()
        resp.json.return_value = json_body
        resp.raise_for_status = MagicMock()
        return resp

    def test_returns_response_on_success(self) -> None:
        with patch("sensor_platform.adapters.ollama_adapter.httpx.Client") as mock_cls:
            ctx = mock_cls.return_value.__enter__.return_value
            ctx.post.return_value = self._mock_httpx({"response": "ollama says hi"})
            adapter = OllamaAdapter()
            assert adapter.generate("sys", "usr") == "ollama says hi"

    def test_raises_llm_error_on_http_error(self) -> None:
        with patch("sensor_platform.adapters.ollama_adapter.httpx.Client") as mock_cls:
            ctx = mock_cls.return_value.__enter__.return_value
            ctx.post.side_effect = httpx.HTTPStatusError(
                "not found", request=MagicMock(), response=MagicMock(status_code=404)
            )
            adapter = OllamaAdapter()
            with pytest.raises(LLMError, match="Ollama HTTP error"):
                adapter.generate("sys", "usr")

    def test_raises_llm_error_on_missing_response_key(self) -> None:
        with patch("sensor_platform.adapters.ollama_adapter.httpx.Client") as mock_cls:
            ctx = mock_cls.return_value.__enter__.return_value
            ctx.post.return_value = self._mock_httpx({"unexpected": "format"})
            adapter = OllamaAdapter()
            with pytest.raises(LLMError, match="Ollama unexpected response"):
                adapter.generate("sys", "usr")

    def test_retries_on_timeout_then_succeeds(self) -> None:
        with patch("sensor_platform.adapters.ollama_adapter.httpx.Client") as mock_cls:
            ctx = mock_cls.return_value.__enter__.return_value
            ctx.post.side_effect = [
                httpx.ReadTimeout("timed out"),
                self._mock_httpx({"response": "ok after retry"}),
            ]
            adapter = OllamaAdapter()
            result = adapter.generate("sys", "usr")
            assert result == "ok after retry"
            assert ctx.post.call_count == 2
