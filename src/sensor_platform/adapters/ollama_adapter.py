"""Ollama adapter — implements LLMClient port via local HTTP API."""

from __future__ import annotations

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from sensor_platform.domain.exceptions import LLMError


class OllamaAdapter:
    def __init__(
        self, base_url: str = "http://localhost:11434", model: str = "llama3.1"
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.TimeoutException),
        reraise=True,
    )
    def generate(self, system: str, user: str, max_tokens: int = 2048) -> str:
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{self._base_url}/api/generate",
                    json={
                        "model": self._model,
                        "system": system,
                        "prompt": user,
                        "stream": False,
                        "options": {"num_predict": max_tokens},
                    },
                )
                resp.raise_for_status()
                return str(resp.json()["response"])
        except httpx.TimeoutException:
            raise
        except httpx.HTTPError as exc:
            raise LLMError(f"Ollama HTTP error: {exc}") from exc
        except (KeyError, ValueError) as exc:
            raise LLMError(f"Ollama unexpected response: {exc}") from exc
