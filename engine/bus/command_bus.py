"""CommandBus — separate channel for intentions (PlaceOrder, CancelOrder).

Idempotency guarantee: same operation_id + sequence never executes twice.
"""
import asyncio
import logging
from typing import Callable, Awaitable

log = logging.getLogger(__name__)
Handler = Callable[..., Awaitable[None]]


class CommandBus:
    """Commands can be rejected. Events are immutable facts.

    Deduplication via operation_id + sequence prevents double execution
    on network timeouts or retries.
    """

    def __init__(self):
        self._handlers: dict[type, list[Handler]] = {}
        self._processed: set[str] = set()
        self._locks: dict[str, asyncio.Lock] = {}

    def subscribe(self, command_type: type, handler: Handler) -> None:
        self._handlers.setdefault(command_type, []).append(handler)

    async def send(self, command) -> bool:
        """Returns True if accepted and executed. False if duplicate."""
        dedup_key = f"{command.operation_id}:{command.sequence}"

        lock = self._locks.setdefault(command.operation_id, asyncio.Lock())
        async with lock:
            if dedup_key in self._processed:
                log.warning("Duplicate command blocked: %s", dedup_key)
                return False

            handlers = self._handlers.get(type(command), [])
            if not handlers:
                return False

            for handler in handlers:
                try:
                    await handler(command)
                except Exception:
                    log.exception("Command handler failed for %s", type(command).__name__)

            self._processed.add(dedup_key)
            return True
