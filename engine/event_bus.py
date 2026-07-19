"""EventBus — central pub/sub event dispatcher."""
import asyncio
import logging
from typing import Callable, Awaitable
from engine.events import Event, EventType

log = logging.getLogger(__name__)

Handler = Callable[[Event], Awaitable[None]]


class EventBus:
    """Publish/subscribe event bus with direct async delivery.

    Each subscriber receives events via direct await — no backlog queues.
    Publishing fans out to all matching subscribers concurrently.
    One slow subscriber does not block others.
    Handler exceptions are logged and do not affect other subscribers.
    """

    def __init__(self):
        self._subscribers: dict[EventType, list[Handler]] = {}
        self._running = True

    def subscribe(self, event_type: EventType, handler: Handler) -> None:
        """Register handler for a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        log.debug("Subscribed %s to %s", handler.__name__, event_type.name)

    def unsubscribe(self, event_type: EventType, handler: Handler) -> None:
        """Remove handler registration for an event type."""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
                log.debug("Unsubscribed %s from %s", handler.__name__, event_type.name)
            except ValueError:
                pass

    def start(self) -> None:
        """Start the event bus (enables publishing)."""
        self._running = True

    async def publish(self, event: Event) -> None:
        """Publish event to all matching subscribers concurrently."""
        if not self._running:
            log.debug("EventBus not running, skipping publish of %s", event.type.name)
            return

        handlers = self._subscribers.get(event.type, [])
        if not handlers:
            return

        tasks = []
        for handler in handlers:
            tasks.append(self._deliver(handler, event))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _deliver(self, handler: Handler, event: Event) -> None:
        """Deliver event to a single handler, catching exceptions."""
        try:
            await handler(event)
        except Exception:
            log.exception(
                "Handler %s failed for event %s (id=%s)",
                handler.__name__, event.type.name, event.event_id,
            )

    async def shutdown(self) -> None:
        """Stop processing events."""
        self._running = False
        log.info("EventBus shut down")
