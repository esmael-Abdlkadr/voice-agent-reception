"""In-memory pub/sub for live events streamed to the dashboard.

Single-process only. If we ever run multiple uvicorn workers we'll swap this
out for Redis pub/sub. For V1 / demo, this is sufficient.

Events are simple JSON-serializable dicts. Each event carries a
`workspace_id` so SSE consumers can filter by which workspaces the
authenticated user is allowed to see.

### sync → async bridge

FastAPI routes defined with `def` (not `async def`) run in a starlette
threadpool. They can't `await publish(event)` directly. We give them
`publish_threadsafe(event)` which schedules the publish on the *real*
event loop. That loop reference is captured once at app startup via
`set_event_loop()` — calling `asyncio.get_event_loop()` from a worker
thread would return a different (dead) loop and silently drop events.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator

log = logging.getLogger(__name__)

_subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
_loop: asyncio.AbstractEventLoop | None = None


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Called once from the FastAPI startup hook."""
    global _loop
    _loop = loop


async def publish(event: dict[str, Any]) -> None:
    """Fan out `event` to every subscriber queue. Drops the event for any
    subscriber whose queue is full (slow consumer)."""
    log.debug("publish event type=%s ws=%s -> %d subs",
              event.get("type"), event.get("workspace_id"), len(_subscribers))
    for queue in list(_subscribers):
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            log.warning("Subscriber queue full; dropping event")


def publish_threadsafe(event: dict[str, Any]) -> None:
    """Schedule `publish(event)` on the captured event loop. Safe to call
    from sync FastAPI handlers (which run in a thread pool) and from any
    other thread."""
    if _loop is None or _loop.is_closed():
        log.warning("publish_threadsafe called but no loop is set; dropping event")
        return
    _loop.call_soon_threadsafe(_schedule_publish, event)


def _schedule_publish(event: dict[str, Any]) -> None:
    """Runs on the event loop thread."""
    asyncio.create_task(publish(event))


async def subscribe() -> AsyncIterator[dict[str, Any]]:
    """Yields each event published while this subscriber is connected."""
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
    _subscribers.add(queue)
    log.info("SSE subscriber attached (total=%d)", len(_subscribers))
    try:
        while True:
            yield await queue.get()
    finally:
        _subscribers.discard(queue)
        log.info("SSE subscriber detached (remaining=%d)", len(_subscribers))


def subscriber_count() -> int:
    return len(_subscribers)
