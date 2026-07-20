"""Tests for TradingEngine — main loop and dispatch."""
import pytest
from engine.trading_engine import TradingEngine
from engine.bus.event_bus import EventBus
from engine.bus.command_bus import CommandBus
from domain.fsm.position_fsm import PositionFSM
from domain.fsm.states import FSMState
from domain.events import AICompleted, OrderFilled


class MockAdapter:
    """Returns empty data for testing."""
    async def fetch_positions(self): return []
    async def fetch_open_orders(self, symbol=None): return []
    async def fetch_balance(self, coin="USDT"): return {}


class MockAI:
    async def request_decision(self, fsm, state):
        pass  # noop


class TestTradingEngine:
    @pytest.mark.asyncio
    async def test_engine_shutdown_clean(self):
        bus = EventBus()
        cmd_bus = CommandBus()
        adapter = MockAdapter()
        ai = MockAI()

        engine = TradingEngine(bus, cmd_bus, adapter, ai, symbols=["BTCUSDT"])
        await engine.shutdown()
        assert engine._running is False

    @pytest.mark.asyncio
    async def test_on_ai_completed_transitions_fsm(self):
        bus = EventBus()
        cmd_bus = CommandBus()
        adapter = MockAdapter()
        ai = MockAI()
        engine = TradingEngine(bus, cmd_bus, adapter, ai, symbols=["BTCUSDT"])

        # Manually register an FSM
        fsm = PositionFSM(symbol="BTCUSDT", side="Sell")
        engine._supervisor.register_fsm(fsm)
        engine._fsms["BTCUSDT_Sell"] = fsm

        decision = {"strategy": "DCA_SHORT", "reasoning": "RSI pump"}
        event = AICompleted(symbol="BTCUSDT", decision=decision, operation_id="op_1", state_version=0)
        await engine.on_ai_completed(event)

        assert fsm.state == FSMState.PREPARING

    @pytest.mark.asyncio
    async def test_stale_ai_decision_ignored(self):
        bus = EventBus()
        cmd_bus = CommandBus()
        engine = TradingEngine(bus, cmd_bus, MockAdapter(), MockAI(), symbols=["BTCUSDT"])

        fsm = PositionFSM(symbol="BTCUSDT", side="Sell")
        fsm.transition(FSMState.PREPARING, trigger="AI", reason="1")  # v=1
        fsm.transition(FSMState.SENDING_ORDER, trigger="timer", reason="2")  # v=2
        engine._supervisor.register_fsm(fsm)
        engine._fsms["BTCUSDT_Sell"] = fsm

        # AI decision with stale version
        event = AICompleted(symbol="BTCUSDT", decision={"strategy": "STALE"}, operation_id="op_1", state_version=0)
        await engine.on_ai_completed(event)

        assert fsm.state == FSMState.SENDING_ORDER  # unchanged
        assert fsm.state_version == 2  # unchanged

    @pytest.mark.asyncio
    async def test_on_order_filled_transitions_to_active(self):
        bus = EventBus()
        cmd_bus = CommandBus()
        engine = TradingEngine(bus, cmd_bus, MockAdapter(), MockAI(), symbols=["BTCUSDT"])

        fsm = PositionFSM(symbol="BTCUSDT", side="Sell", initial_state=FSMState.WAIT_FILL)
        engine._supervisor.register_fsm(fsm)
        engine._fsms["BTCUSDT_Sell"] = fsm

        event = OrderFilled(order_id="1", symbol="BTCUSDT", side="Sell", qty=0.005, price=67200.0)
        await engine.on_order_filled(event)

        assert fsm.state == FSMState.ACTIVE
