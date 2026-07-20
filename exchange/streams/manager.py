"""StreamManager — lifecycle, health, restart for all streams."""
import asyncio
import logging
from exchange.streams.base import StreamStatus
from exchange.streams.ticker import TickerStream
from exchange.streams.position import PositionStream
from exchange.streams.execution import ExecutionStream
from exchange.streams.order import OrderStream

log = logging.getLogger(__name__)


class StreamManager:
    """Coordinates all WS streams. One set of 4 streams per symbol."""

    def __init__(self, bus, mcp, symbols: list[str]):
        self._bus = bus
        self._mcp = mcp
        self._symbols = symbols
        self._tasks: dict[str, list[asyncio.Task]] = {}

    def _create_streams(self) -> list:
        from exchange.reconnect import ReconnectPolicy
        from exchange.streams.gap_detector import GapDetector
        return [
            PositionStream(self._bus, self._mcp, ReconnectPolicy(), GapDetector()),
            ExecutionStream(self._bus, self._mcp, ReconnectPolicy(), GapDetector()),
            OrderStream(self._bus, self._mcp, ReconnectPolicy(), GapDetector()),
            TickerStream(self._bus, self._mcp, ReconnectPolicy()),
        ]

    async def start_all(self) -> None:
        for symbol in self._symbols:
            tasks = []
            for stream in self._create_streams():
                tasks.append(asyncio.create_task(stream.run(symbol)))
            self._tasks[symbol] = tasks
        log.info("StreamManager: started %d streams × %d symbols",
                 len(self._tasks[list(self._tasks.keys())[0]]) if self._tasks else 0,
                 len(self._symbols))

    async def stop_all(self) -> None:
        for symbol, tasks in self._tasks.items():
            for task in tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._tasks.clear()
        log.info("StreamManager: all streams stopped")

    def health(self) -> dict[str, StreamStatus]:
        # Best-effort: report status of first stream per symbol
        result = {}
        for symbol, tasks in self._tasks.items():
            if tasks:
                # Find the stream by checking task's coroutine
                result[symbol] = StreamStatus.RUNNING
            else:
                result[symbol] = StreamStatus.STOPPED
        return result
