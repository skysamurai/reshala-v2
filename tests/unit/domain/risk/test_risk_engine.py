"""Tests for Risk Engine — Level 1/2/3 guards."""
import pytest
from domain.risk.engine import RiskEngine, RiskLimits
from domain.events import OrderFilled, PositionChanged, RiskLimitHit, EventType


class TestRiskLimits:
    def test_default_limits(self):
        limits = RiskLimits()
        assert limits.max_position_size_usd == 500.0
        assert limits.max_dca_per_position == 5
        assert limits.daily_loss_cap_usd == 500.0
        assert limits.max_concurrent_positions == 5


class TestRiskEngineLevel1:
    """Level 1: Per-trade limits."""

    def test_position_size_within_limit(self):
        engine = RiskEngine(RiskLimits(max_position_size_usd=500.0))
        result = engine.check_order_size("BTCUSDT", 0.005, 67000.0)  # 335 USD
        assert result is True

    def test_position_size_exceeds_limit(self):
        engine = RiskEngine(RiskLimits(max_position_size_usd=500.0))
        result = engine.check_order_size("BTCUSDT", 0.1, 67000.0)  # 6700 USD
        assert result is False

    def test_max_dca_not_exceeded(self):
        engine = RiskEngine(RiskLimits(max_dca_per_position=3))
        engine.record_dca("BTCUSDT_Sell")
        engine.record_dca("BTCUSDT_Sell")
        assert engine.can_dca("BTCUSDT_Sell") is True

    def test_max_dca_exceeded(self):
        engine = RiskEngine(RiskLimits(max_dca_per_position=2))
        engine.record_dca("BTCUSDT_Sell")
        engine.record_dca("BTCUSDT_Sell")
        assert engine.can_dca("BTCUSDT_Sell") is False


class TestRiskEngineLevel2:
    """Level 2: Global limits."""

    def test_daily_loss_not_exceeded(self):
        engine = RiskEngine(RiskLimits(daily_loss_cap_usd=500.0))
        engine.record_realised_loss("BTCUSDT", 200.0)
        assert engine.check_daily_loss() is True

    def test_daily_loss_exceeded_publishes_event(self):
        engine = RiskEngine(RiskLimits(daily_loss_cap_usd=100.0))

        event = engine.record_realised_loss("BTCUSDT", 150.0)
        assert event is not None
        assert event.limit_type == "daily_loss"
        assert engine.check_daily_loss() is False

    def test_max_concurrent_positions(self):
        limits = RiskLimits(max_concurrent_positions=2)
        engine = RiskEngine(limits)
        assert engine.can_open_position(current_count=1) is True
        assert engine.can_open_position(current_count=2) is False


class TestRiskEngineLevel3:
    """Level 3: System/circuit breaker."""

    def test_consecutive_errors_trigger_circuit_breaker(self):
        engine = RiskEngine(RiskLimits(max_consecutive_errors=3))
        engine.record_error()
        engine.record_error()
        assert engine.is_circuit_open() is False
        engine.record_error()
        assert engine.is_circuit_open() is True

    def test_circuit_breaker_resets(self):
        engine = RiskEngine(RiskLimits(max_consecutive_errors=2))
        engine.record_error()
        engine.record_error()
        assert engine.is_circuit_open() is True
        engine.reset_errors()
        assert engine.is_circuit_open() is False


class TestRiskEngineEvents:
    def test_publishes_risk_limit_hit(self):
        engine = RiskEngine(RiskLimits(max_position_size_usd=100.0))
        event = engine.check_and_warn("BTCUSDT", "position_size", "size=1.0 exceeds 100 USD")
        assert event is not None
        assert event.type == EventType.RISK_LIMIT_HIT
        assert event.limit_type == "position_size"
        assert event.symbol == "BTCUSDT"
