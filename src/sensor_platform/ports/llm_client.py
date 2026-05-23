"""LLM client port — abstract interface for text generation."""

from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    def generate(self, system: str, user: str, max_tokens: int = 2048) -> str:
        """Generate text from system + user prompts. Raises LLMError on failure."""
        ...
