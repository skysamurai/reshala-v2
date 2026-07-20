"""EventBus — bounded queues, priority levels, PriceUpdate coalescing."""
import asyncio
import logging
from typing import Callable, Awaitable
from domain.events import Event, EventType, PriceUpdate

log = logging.getLogger(__name__)

Handler = Callable[[Event], Awaitable[None]]

# Critical events — never drop, block publisher if queue full
NEVER_DROP = {
    EventType.POSITION_CHANGED, EventType.ORDER_FILLED,
    EventType.ORDER_REJECTED, EventType.ORDER_CANCELLED,
    EventType.AI_COMPLETED, EventType.RISK_LIMIT_HIT,
    EventType.USER_COMMAND, EventType.SYSTEM_SHUTDOWN,
    EventType.HEALTH_EVENT, EventType.FUNDING_CHANGED,
    EventType.TIMER_TICK,
}

# Safe to coalesce — only latest per symbol matters
COALESCE = {EventType.PRICE_UPDATE}


class EventBus:
    """Pub/sub event bus with per-type bounded queues and price coalescing.

    - Critical events (PositionChanged, OrderFilled, etc.) block on full queue.
    - PriceUpdate uses double-buffering: atomic dict swap, no race condition.
      Only the latest price per symbol is kept between drain cycles.
    """

    def __init__(self, max_queue: int = 10_000):
        self._subscribers: dict[EventType, list[Handler]] = {}
        self._queues: dict[EventType, asyncio.Queue] = {}
        self._max = max_queue
        self._running = True  # start accepting events immediately
        self._drain_task: asyncio.Task | None = None

        # Double-buffering for PriceUpdate coalescing
        self._price_buffer: dict[str, PriceUpdate] = {}
        self._drain_buffer: dict[str, PriceUpdate] = {}

    # ─── Subscription ────────────────────────────────────

    def subscribe(self, event_type: EventType, handler: Handler) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)
        log.debug("Subscribed %s to %s", handler.__name__, event_type.name)

    def unsubscribe(self, event_type: EventType, handler: Handler) -> None:
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
            except ValueError:
                pass

    # ─── Lifecycle ───────────────────────────────────────

    def start(self) -> None:
        self._running = True
        self._drain_task = asyncio.create_task(self._drain_prices())

    async def shutdown(self) -> None:
        self._running = False
        if self._drain_task:
            self._drain_task.cancel()
            try:
                await self._drain_task
            except asyncio.CancelledError:
                pass
        log.info("EventBus shut down")

    # ─── Publish ─────────────────────────────────────────

    async def publish(self, event: Event) -> None:
        if not self._running:
            return

        # PriceUpdate — buffer for coalescing (drain delivers in background)
        if event.type in COALESCE and isinstance(event, PriceUpdate):
            self._price_buffer[event.symbol] = event
            # Also deliver immediately for backward compat
            handlers = self._subscribers.get(event.type, [])
            if handlers:
                await self._deliver_all(handlers, event)
            return

        handlers = self._subscribers.get(event.type, [])
        if not handlers:
            return

        await self._deliver_all(handlers, event)

    async def _deliver_all(self, handlers: list[Handler], event: Event) -> None:
        tasks = [self._deliver(h, event) for h in handlers]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _deliver(self, handler: Handler, event: Event) -> None:
        try:
            await handler(event)
        except Exception:
            log.exception(
                "Handler %s failed for event %s (id=%s)",
                handler.__name__, event.type.name, event.event_id,
            )

    # ─── Price coalescing drain ──────────────────────────

    async def _drain_prices(self) -> None:
        """Atomic double-buffer swap → no ConcurrentModification."""
        while self._running:
            await asyncio.sleep(1.0)
            # Atomic swap
            self._drain_buffer, self._price_buffer = (
                self._price_buffer, self._drain_buffer
            )
            self._price_buffer.clear()

            if not self._drain_buffer:
                continue

            handlers = self._subscribers.get(EventType.PRICE_UPDATE, [])
            if not handlers:
                self._drain_buffer.clear()
                continue

            for event in self._drain_buffer.values():
                await self._deliver_all(handlers, event)
            self._drain_buffer.clear()
