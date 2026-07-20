"""Tests for ExchangeState."""
import pytest
from domain.exchange_state import ExchangeState
from domain.events import PositionChanged, OrderFilled, PriceUpdate, EventType


class TestExchangeStateApply:
    def test_apply_position_changed(self):
        state = ExchangeState()
        event = PositionChanged(
            symbol="BTCUSDT", side="Sell", size=0.01,
            unrealised_pnl=-200.0, margin=500.0,
        )
        state.apply(event)

        pos = state.get_position("BTCUSDT")
        assert pos is not None
        assert pos["size"] == 0.01
        assert pos["unrealised_pnl"] == -200.0

    def test_apply_multiple_events_increments_version(self):
        state = ExchangeState()
        assert state.version == 0
        state.apply(PositionChanged(symbol="BTCUSDT"))
        assert state.version == 1  # PositionChanged → increments
        state.apply(PositionChanged(symbol="ETHUSDT"))
        assert state.version == 2  # PositionChanged → increments
        state.apply(OrderFilled(order_id="1", symbol="BTCUSDT", side="Sell", qty=0.01, price=67000.0))
        assert state.version == 3  # OrderFilled → increments

    def test_get_position_none_for_unknown(self):
        state = ExchangeState()
        assert state.get_position("UNKNOWN") is None

    def test_has_open_orders(self):
        state = ExchangeState()
        # Initially no orders
        assert state.has_open_orders("BTCUSDT") is False

    def test_snapshot_roundtrip(self):
        state = ExchangeState()
        state.apply(PositionChanged(symbol="BTCUSDT", side="Sell", size=0.01, unrealised_pnl=-200.0))
        state.apply(PriceUpdate(symbol="BTCUSDT", price=67000.0))

        snap = state.snapshot()
        restored = ExchangeState.from_snapshot(snap)

        assert restored.get_position("BTCUSDT")["size"] == 0.01
        assert restored.version == state.version

    def test_position_history_for_ai(self):
        state = ExchangeState()
        state.apply(PositionChanged(symbol="BTCUSDT", side="Sell", size=0.01, unrealised_pnl=-200.0))
        state.apply(PositionChanged(symbol="BTCUSDT", side="Sell", size=0.02, unrealised_pnl=-400.0))
        state.apply(PositionChanged(symbol="ETHUSDT", side="Sell", size=0.1, unrealised_pnl=-300.0))

        history = state.get_position_history("BTCUSDT")
        assert len(history) == 2
        assert all(e.symbol == "BTCUSDT" for e in history)

    def test_version_only_increments_on_state_changing_events(self):
        """Only position/order events change version. PriceUpdate does not."""
        state = ExchangeState()
        state.apply(PositionChanged(symbol="BTCUSDT"))  # v=1
        state.apply(PriceUpdate(symbol="BTCUSDT", price=67000.0))  # v=1, no change
        assert state.version == 1  # PriceUpdate doesn't increment version
