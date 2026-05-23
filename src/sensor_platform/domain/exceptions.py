"""Domain exceptions — no HTTP or framework dependencies."""

from __future__ import annotations


class LLMError(Exception):
    """LLM generation failed (API error, timeout, exhausted retries)."""


class LLMConfigError(Exception):
    """Invalid LLM configuration (missing API key, unknown provider)."""
