"""BaseStream — common logic for all Bybit WS streams."""
import asyncio
import logging
from enum import Enum

log = logging.getLogger(__name__)


class StreamStatus(Enum):
    STARTING = "starting"
    RUNNING = "running"
    RECONNECTING = "reconnecting"
    STOPPED = "stopped"
    FAILED = "failed"


class BaseStream:
    """Base class for all stream producers. Publishes typed Events to EventBus."""

    def __init__(self, bus, mcp=None, reconnect=None, gap_detector=None):
        self._bus = bus
        self._mcp = mcp
        self._reconnect = reconnect
        self._gap = gap_detector
        self._running = False
        self._seq: int = 0
        self.status: StreamStatus = StreamStatus.STARTING

    @property
    def category(self) -> str:
        return "linear"

    @property
    def topic_prefix(self) -> str:
        raise NotImplementedError

    def topic(self, symbol: str) -> str:
        return f"{self.topic_prefix}.{symbol}"

    def map_event(self, raw: dict):
        """Convert raw Bybit message → domain Event. Override in subclass."""
        raise NotImplementedError

    async def run(self, symbol: str) -> None:
        self._running = True
        self.status = StreamStatus.RUNNING

        while self._running:
            try:
                sub_id = await self._mcp.start_subscription(
                    category=self.category, topic=self.topic(symbol)
                )
                await self._consume(sub_id, symbol)
            except Exception:
                if not self._running:
                    break
                self.status = StreamStatus.RECONNECTING
                log.warning("%s: reconnect for %s", type(self).__name__, symbol)
                if self._reconnect:
                    await self._reconnect.wait()
                self.status = StreamStatus.RUNNING

    async def _consume(self, sub_id: str, symbol: str) -> None:
        while self._running:
            messages = await self._mcp.read_messages(sub_id, limit=50)
            for raw in messages:
                if self._gap and self._gap.check(raw):
                    log.warning("%s: sequence gap for %s", type(self).__name__, symbol)
                event = self.map_event(raw)
                if event:
                    event.sequence = self._next_seq()
                    await self._bus.publish(event)
            await asyncio.sleep(1.0)  # heartbeat

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    async def stop(self) -> None:
        self._running = False
        self.status = StreamStatus.STOPPED
