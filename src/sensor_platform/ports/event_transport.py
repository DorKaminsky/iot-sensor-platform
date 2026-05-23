"""EventTransport protocol — abstract interface for consuming sensor events."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol


class EventTransport(Protocol):
    def consume(self) -> Iterator[dict]:  # type: ignore[type-arg]
        """Yield raw event dicts; stop iteration when stream ends."""
        ...
