"""queue.Queue implementation of EventTransport."""

from __future__ import annotations

import queue
from collections.abc import Iterator
from typing import Any


class QueueTransport:
    """Wraps a queue.Queue produced by SensorEventProducer.

    Yields event dicts until the producer sends the None sentinel.
    Swapping this for RedisTransport only requires changing the injected transport,
    not the consumer logic.
    """

    def __init__(self, q: queue.Queue[dict[str, Any] | None]) -> None:
        self._queue = q

    def consume(self) -> Iterator[dict[str, Any]]:
        while True:
            event = self._queue.get()
            if event is None:
                return
            yield event
