"""Tests for EventBus."""
import asyncio
import pytest
from engine.event_bus import EventBus
from engine.events import PriceUpdate, OrderFilled, EventType, TimerTick, SystemShutdown


class TestEventBus:
    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe(EventType.PRICE_UPDATE, handler)
        event = PriceUpdate(symbol="BTCUSDT", price=67000.0, high=67100.0, low=66900.0, volume=100.0)
        await bus.publish(event)

        await asyncio.sleep(0.1)
        assert len(received) == 1
        assert received[0].symbol == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_multiple_subscribers_same_event(self):
        bus = EventBus()
        results_a = []
        results_b = []

        bus.subscribe(EventType.PRICE_UPDATE, lambda e: results_a.append(e))
        bus.subscribe(EventType.PRICE_UPDATE, lambda e: results_b.append(e))

        await bus.publish(PriceUpdate(symbol="ETHUSDT", price=3200.0, high=3210.0, low=3190.0, volume=50.0))
        await asyncio.sleep(0.1)

        assert len(results_a) == 1
        assert len(results_b) == 1
        assert results_a[0].symbol == "ETHUSDT"

    @pytest.mark.asyncio
    async def test_handler_gets_only_subscribed_type(self):
        bus = EventBus()
        prices = []
        fills = []

        bus.subscribe(EventType.PRICE_UPDATE, lambda e: prices.append(e))
        bus.subscribe(EventType.ORDER_FILLED, lambda e: fills.append(e))

        await bus.publish(PriceUpdate(symbol="BTCUSDT", price=67000.0, high=67100.0, low=66900.0, volume=100.0))
        await bus.publish(OrderFilled(order_id="1", order_link_id="L1", symbol="BTCUSDT", side="Sell", qty=0.01, price=67100.0))
        await asyncio.sleep(0.1)

        assert len(prices) == 1
        assert len(fills) == 1

    @pytest.mark.asyncio
    async def test_handler_exception_does_not_block_others(self):
        bus = EventBus()
        good = []

        async def bad_handler(event):
            raise RuntimeError("handler crash")

        async def good_handler(event):
            good.append(event)

        bus.subscribe(EventType.PRICE_UPDATE, bad_handler)
        bus.subscribe(EventType.PRICE_UPDATE, good_handler)

        await bus.publish(PriceUpdate(symbol="BTCUSDT", price=67000.0, high=67100.0, low=66900.0, volume=100.0))
        await asyncio.sleep(0.1)

        assert len(good) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe(EventType.PRICE_UPDATE, handler)
        await bus.publish(PriceUpdate(symbol="BTCUSDT", price=67000.0, high=67100.0, low=66900.0, volume=100.0))
        await asyncio.sleep(0.1)
        assert len(received) == 1

        bus.unsubscribe(EventType.PRICE_UPDATE, handler)
        await bus.publish(PriceUpdate(symbol="BTCUSDT", price=68000.0, high=68100.0, low=67900.0, volume=200.0))
        await asyncio.sleep(0.1)
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_shutdown_stops_processing(self):
        bus = EventBus()
        bus.start()
        received = []

        bus.subscribe(EventType.TIMER_TICK, lambda e: received.append(e))
        await bus.publish(TimerTick())
        await asyncio.sleep(0.1)
        assert len(received) == 1

        await bus.shutdown()
        await bus.publish(TimerTick())
        await asyncio.sleep(0.1)
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_publish_many_events(self):
        bus = EventBus()
        count = 0

        async def counter(event):
            nonlocal count
            count += 1

        bus.subscribe(EventType.PRICE_UPDATE, counter)
        for i in range(100):
            await bus.publish(PriceUpdate(symbol="BTCUSDT", price=67000.0 + i, high=67100.0, low=66900.0, volume=100.0))

        await asyncio.sleep(0.3)
        assert count == 100
