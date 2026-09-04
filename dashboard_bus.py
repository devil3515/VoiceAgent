"""
In-process event bus used by the dashboard.

`publish(event_dict)` broadcasts a dict to every active subscriber.
Subscribers get an asyncio.Queue; if a queue is full we drop the event
and bump a counter rather than blocking the publisher.
"""

from __future__ import annotations

import asyncio
from typing import Any
from datetime import datetime, timezone


class EventBus:
    def __init__(self, max_queue: int = 256) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._max_queue = max_queue
        self._dropped = 0

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self._max_queue)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.discard(q)

    def publish(self, event: str, **fields: Any) -> None:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **fields,
        }
        # Iterate over a copy so a subscriber dying during iteration is safe.
        for q in list(self._subscribers):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                self._dropped += 1

    @property
    def dropped(self) -> int:
        return self._dropped


# Singleton used by main.py and the structlog processor.
bus = EventBus()
