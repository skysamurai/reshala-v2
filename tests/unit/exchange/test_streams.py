"""Tests for streams with mock MCP."""
import asyncio
import pytest
from engine.bus.event_bus import EventBus
from domain.events import EventType, PriceUpdate, PositionChanged
from exchange.streams.ticker import TickerStream
from exchange.streams.position import PositionStream
from exchange.streams.execution import ExecutionStream


class MockMCP:
    """Mock Bybit MCP for testing streams."""
    def __init__(self, messages: list[dict] = None, delay: float = 0.0):
        self.messages = messages or []
        self.subscriptions: dict[str, str] = {}  # topic → sub_id
        self._running = True

    async def start_subscription(self, category: str, topic: str) -> str:
        sub_id = f"sub_{topic}"
        self.subscriptions[topic] = sub_id
        return sub_id

    async def read_messages(self, sub_id: str, limit: int = 50):
        await asyncio.sleep(0.01)
        result = self.messages[:limit]
        self.messages = self.messages[limit:]
        return result


class TestTickerStream:
    @pytest.mark.asyncio
    async def test_publishes_price_update(self):
        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe(EventType.PRICE_UPDATE, handler)

        mcp = MockMCP(messages=[
            {"symbol": "BTCUSDT", "lastPrice": "67000.0", "highPrice24h": "67100.0",
             "lowPrice24h": "66900.0", "volume24h": "100.0"},
        ])

        stream = TickerStream(bus, mcp)
        task = asyncio.create_task(stream.run("BTCUSDT"))
        await asyncio.sleep(0.1)
        await stream.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert len(received) >= 1
        assert received[0].symbol == "BTCUSDT"
        assert received[0].price == 67000.0


class TestPositionStream:
    @pytest.mark.asyncio
    async def test_publishes_position_changed(self):
        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe(EventType.POSITION_CHANGED, handler)

        mcp = MockMCP(messages=[
            {"symbol": "BTCUSDT", "side": "Sell", "size": "0.01",
             "positionIM": "500.0", "unrealisedPnl": "-200.0",
             "cumRealisedPnl": "0.0", "liqPrice": "72000.0"},
        ])

        stream = PositionStream(bus, mcp)
        task = asyncio.create_task(stream.run("BTCUSDT"))
        await asyncio.sleep(0.1)
        await stream.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert len(received) >= 1
        assert received[0].symbol == "BTCUSDT"
        assert received[0].size == 0.01


class TestExecutionStream:
    @pytest.mark.asyncio
    async def test_publishes_order_filled(self):
        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe(EventType.ORDER_FILLED, handler)

        mcp = MockMCP(messages=[
            {"orderId": "ord_1", "orderLinkId": "L1", "symbol": "BTCUSDT",
             "side": "Sell", "execQty": "0.005", "execPrice": "67200.0"},
        ])

        stream = ExecutionStream(bus, mcp)
        task = asyncio.create_task(stream.run("BTCUSDT"))
        await asyncio.sleep(0.1)
        await stream.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert len(received) >= 1
        assert received[0].order_id == "ord_1"
