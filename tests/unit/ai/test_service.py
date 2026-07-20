"""Tests for AIService."""
import asyncio
import pytest
from ai.service import AIService
from domain.fsm.position_fsm import PositionFSM
from domain.exchange_state import ExchangeState
from domain.events import PositionChanged, EventType
from engine.bus.event_bus import EventBus


class MockProvider:
    async def decide(self, symbol, position, history):
        return {"strategy": "DCA_SHORT", "reasoning": "test decision"}


class TestAIService:
    @pytest.mark.asyncio
    async def test_decision_publishes_ai_completed(self):
        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe(EventType.AI_COMPLETED, handler)

        state = ExchangeState()
        state.apply(PositionChanged(symbol="BTCUSDT", side="Sell", size=0.01, unrealised_pnl=-200.0))

        fsm = PositionFSM(symbol="BTCUSDT", side="Sell")
        ai = AIService(bus, provider=MockProvider())
        await ai.request_decision(fsm, state)

        # Wait for async task
        await asyncio.sleep(0.1)

        assert len(received) == 1
        assert received[0].symbol == "BTCUSDT"
        assert received[0].decision["strategy"] == "DCA_SHORT"
        assert received[0].correlation_id != ""  # has correlation ID
