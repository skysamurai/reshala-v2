"""Tests for event type definitions."""
import uuid
from datetime import datetime, timezone
from engine.events import (
    EventType,
    Event,
    PriceUpdate,
    OrderFilled,
    PositionChanged,
    AICompleted,
    TimerTick,
    RiskLimitHit,
    SystemShutdown,
)


class TestEventTypes:
    def test_event_type_enum_has_all_types(self):
        """All expected event types exist in the enum."""
        expected = {
            "PRICE_UPDATE", "ORDER_FILLED", "ORDER_REJECTED", "ORDER_CANCELLED",
            "POSITION_CHANGED", "FUNDING_CHANGED", "AI_COMPLETED",
            "TIMER_TICK", "RISK_LIMIT_HIT", "USER_COMMAND", "SYSTEM_SHUTDOWN",
        }
        actual = {e.name for e in EventType}
        assert expected.issubset(actual)

    def test_price_update_event(self):
        e = PriceUpdate(symbol="BTCUSDT", price=67000.0, high=67100.0, low=66900.0, volume=1234.5)
        assert e.type == EventType.PRICE_UPDATE
        assert e.symbol == "BTCUSDT"
        assert e.price == 67000.0
        assert e.timestamp is not None

    def test_order_filled_event(self):
        e = OrderFilled(
            order_id="ord_123", order_link_id="BTCUSDT_DCA_abc_1",
            symbol="BTCUSDT", side="Sell", qty=0.01, price=67100.0,
        )
        assert e.type == EventType.ORDER_FILLED
        assert e.order_id == "ord_123"

    def test_position_changed_event(self):
        e = PositionChanged(
            symbol="BTCUSDT", side="Sell", size=0.02, margin=1000.0,
            unrealised_pnl=-200.0, roe_percent=-20.0, liq_price=72000.0,
        )
        assert e.type == EventType.POSITION_CHANGED
        assert e.size == 0.02

    def test_ai_completed_event_carries_state_version(self):
        decision = {"strategy": "WAIT", "reasoning": "test"}
        e = AICompleted(decision=decision, operation_id="op_123", state_version=42)
        assert e.type == EventType.AI_COMPLETED
        assert e.state_version == 42
        assert e.decision["strategy"] == "WAIT"

    def test_timer_tick_event(self):
        e = TimerTick()
        assert e.type == EventType.TIMER_TICK
        assert isinstance(e.timestamp, datetime)

    def test_risk_limit_hit_event(self):
        e = RiskLimitHit(limit_type="daily_loss", symbol="BTCUSDT", current_value=-150.0, threshold=100.0)
        assert e.type == EventType.RISK_LIMIT_HIT
        assert e.limit_type == "daily_loss"

    def test_system_shutdown_event(self):
        e = SystemShutdown(reason="user_request")
        assert e.type == EventType.SYSTEM_SHUTDOWN

    def test_event_id_is_unique_uuid(self):
        e1 = PriceUpdate(symbol="BTCUSDT", price=67000.0, high=67100.0, low=66900.0, volume=100.0)
        e2 = PriceUpdate(symbol="BTCUSDT", price=67000.0, high=67100.0, low=66900.0, volume=100.0)
        assert e1.event_id != e2.event_id
        uuid.UUID(e1.event_id)  # does not raise
