"""Anthropic Claude adapter — implements LLMClient port."""

from __future__ import annotations

import anthropic
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from sensor_platform.domain.exceptions import LLMError


class ClaudeAdapter:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5") -> None:
        self._client = anthropic.Anthropic(api_key=api_key, timeout=30.0)
        self._model = model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(anthropic.APITimeoutError),
        reraise=True,
    )
    def generate(self, system: str, user: str, max_tokens: int = 2048) -> str:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            block = response.content[0]
            if not hasattr(block, "text"):
                raise LLMError("Unexpected response block type from Claude")
            return str(block.text)
        except anthropic.APITimeoutError:
            raise
        except anthropic.APIError as exc:
            raise LLMError(f"Claude API error: {exc}") from exc
