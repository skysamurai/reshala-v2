"""ReconnectPolicy — exponential backoff for stream reconnection."""
import asyncio
import logging

log = logging.getLogger(__name__)


class ReconnectPolicy:
    BACKOFF = [1, 2, 5, 10, 30, 60]  # seconds

    def __init__(self):
        self._attempt = 0

    @property
    def next_delay(self) -> int:
        return self.BACKOFF[min(self._attempt, len(self.BACKOFF) - 1)]

    def next(self) -> int:
        """Increment attempt and return delay (without sleeping). For testing."""
        delay = self.next_delay
        self._attempt += 1
        return delay

    async def wait(self) -> None:
        delay = self.next()
        log.debug("Reconnect attempt %d, waiting %ds", self._attempt, delay)
        await asyncio.sleep(delay)

    def reset(self) -> None:
        self._attempt = 0
