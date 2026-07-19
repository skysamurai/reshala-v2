"""Integration tests — all components working together."""
import asyncio
import pytest
from engine.event_bus import EventBus
from engine.event_logger import EventLogger
from engine.events import (
    PriceUpdate, OrderFilled, AICompleted, PositionChanged,
    EventType, RiskLimitHit, UserCommand, SystemShutdown,
)
from engine.fsm.position_fsm import PositionFSM
from engine.fsm.states import FSMState, ActiveSubState, WaitReason
from engine.fsm.supervisor import GlobalSupervisor
from engine.recovery import RecoveryManager
import tempfile
import os


class TestFullFlow:
    """Test the complete flow: EventBus → FSM → Logger."""

    @pytest.mark.asyncio
    async def test_idle_to_active_via_events(self):
        bus = EventBus()
        bus.start()
        log_dir = tempfile.mkdtemp()
        log_path = os.path.join(log_dir, "events.jsonl")
        logger = EventLogger(log_path)
        supervisor = GlobalSupervisor()

        fsm = PositionFSM(symbol="BTCUSDT", side="Sell")
        supervisor.register_fsm(fsm)

        async def fsm_handler(event):
            """Simulate FSM receiving events and transitioning."""
            if fsm.state == FSMState.IDLE and event.type == EventType.AI_COMPLETED:
                ok = fsm.transition(FSMState.PREPARING, trigger="AICompleted",
                                    reason=event.decision.get("reasoning", ""),
                                    operation_id=event.operation_id)
                if ok:
                    await logger.log_transition(
                        symbol=fsm.symbol, from_state=FSMState.IDLE,
                        to_state=FSMState.PREPARING, trigger="AICompleted",
                        reason=event.decision.get("reasoning", ""),
                        operation_id=event.operation_id,
                        state_version=fsm.state_version,
                    )
            elif fsm.state == FSMState.WAIT_FILL and event.type == EventType.ORDER_FILLED:
                fsm.transition(FSMState.ACTIVE, trigger="OrderFilled", reason="DCA filled")

            supervisor.touch(supervisor._fsm_key(fsm.symbol, fsm.side))

        bus.subscribe(EventType.AI_COMPLETED, fsm_handler)
        bus.subscribe(EventType.ORDER_FILLED, fsm_handler)

        # Simulate AI decision
        decision = {"strategy": "DCA_SHORT", "reasoning": "RSI 5m > 65, pump 0.8%"}
        await bus.publish(AICompleted(decision=decision, operation_id="op_test", state_version=0))
        await asyncio.sleep(0.1)

        # FSM should now be in PREPARING
        assert fsm.state == FSMState.PREPARING

        # Manually advance through SENDING_ORDER, VERIFY, WAIT_FILL
        assert fsm.transition(FSMState.SENDING_ORDER, trigger="test", reason="params valid")
        assert fsm.transition(FSMState.VERIFY, trigger="test", reason="order sent")
        assert fsm.transition(FSMState.WAIT_FILL, trigger="test", reason="order confirmed")
        assert fsm.state == FSMState.WAIT_FILL

        # Simulate order fill
        await bus.publish(OrderFilled(
            order_id="ord_1", order_link_id="BTCUSDT_DCA_abc_1",
            symbol="BTCUSDT", side="Sell", qty=0.005, price=67200.0,
        ))
        await asyncio.sleep(0.1)

        assert fsm.state == FSMState.ACTIVE
        assert fsm.state_version > 0

        await logger.close()
        await bus.shutdown()

        # Verify event log was written
        log_files = os.listdir(log_dir)
        assert len(log_files) >= 1


class TestRecoveryIntegration:
    def test_recovery_manager_creates_fsms_correctly(self):
        """RecoveryManager → PositionFSM → GlobalSupervisor chain."""
        mgr = RecoveryManager()
        supervisor = GlobalSupervisor()

        positions = [
            {"symbol": "BTCUSDT", "side": "Sell", "size": 0.01,
             "avg_price": 65000.0, "mark_price": 67000.0,
             "unrealised_pnl": -200.0, "cum_realised_pnl": 0.0,
             "roe_percent": -40.0, "margin": 500.0, "leverage": 7,
             "liq_price": 72000.0, "take_profit": 0.0},
            {"symbol": "ETHUSDT", "side": "Sell", "size": 0.1,
             "avg_price": 3200.0, "mark_price": 3400.0,
             "unrealised_pnl": -200.0, "cum_realised_pnl": 0.0,
             "roe_percent": -40.0, "margin": 500.0, "leverage": 7,
             "liq_price": 3800.0, "take_profit": 0.0},
        ]

        fsms = mgr.reconcile(positions=positions, open_orders=[], execution_history=[])
        for fsm in fsms:
            supervisor.register_fsm(fsm)

        assert len(supervisor.fsms) == 2
        assert supervisor.state.name == "HEALTHY"


class TestRiskFlow:
    """Risk limit → Supervisor → FSM pause chain."""

    def test_risk_limit_pauses_fsms(self):
        supervisor = GlobalSupervisor()
        fsm = PositionFSM(symbol="BTCUSDT", side="Sell")
        supervisor.register_fsm(fsm)

        # Before risk hit
        assert fsm.is_trading()

        # Risk limit hits
        event = RiskLimitHit(limit_type="daily_loss", symbol="BTCUSDT",
                             current_value=-200.0, threshold=100.0)
        supervisor.handle_risk_limit(event)

        # Supervisor is now in RISK_LIMITED
        assert supervisor.is_risk_limited()

        # FSM can be transitioned to PAUSED_RISK
        result = fsm.transition(FSMState.PAUSED_RISK, trigger="RiskLimitHit",
                                reason="Daily loss cap reached")
        assert result is True
        assert not fsm.is_trading()

    def test_clear_risk_restores_trading(self):
        supervisor = GlobalSupervisor()
        fsm = PositionFSM(symbol="BTCUSDT", side="Sell")
        supervisor.register_fsm(fsm)

        supervisor.handle_risk_limit(RiskLimitHit(
            limit_type="daily_loss", symbol="BTCUSDT",
            current_value=-200.0, threshold=100.0,
        ))
        fsm.transition(FSMState.PAUSED_RISK, trigger="RiskLimitHit", reason="daily loss cap")

        # User acknowledges risk
        supervisor.clear_risk_limit("daily_loss")
        assert not supervisor.is_risk_limited()

        # FSM can resume
        result = fsm.transition(FSMState.IDLE, trigger="RiskCleared",
                                reason="User acknowledged risk")
        assert result is True
        assert fsm.is_trading()
