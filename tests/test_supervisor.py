"""Tests for GlobalSupervisor."""
import pytest
from engine.fsm.supervisor import GlobalSupervisor, SupervisorState
from engine.fsm.position_fsm import PositionFSM
from engine.fsm.states import FSMState
from engine.event_bus import EventBus
from engine.events import RiskLimitHit


class TestSupervisorCreation:
    def test_supervisor_starts_healthy(self):
        sup = GlobalSupervisor()
        assert sup.state == SupervisorState.HEALTHY

    def test_supervisor_registers_position_fsms(self):
        sup = GlobalSupervisor()
        fsm_btc = PositionFSM(symbol="BTCUSDT", side="Sell")
        fsm_eth = PositionFSM(symbol="ETHUSDT", side="Sell")

        sup.register_fsm(fsm_btc)
        sup.register_fsm(fsm_eth)

        assert len(sup.fsms) == 2
        assert "BTCUSDT_Sell" in sup.fsms
        assert "ETHUSDT_Sell" in sup.fsms

    def test_supervisor_unregisters_closed_fsm(self):
        sup = GlobalSupervisor()
        fsm = PositionFSM(symbol="BTCUSDT", side="Sell")
        sup.register_fsm(fsm)
        sup.unregister_fsm("BTCUSDT", "Sell")
        assert len(sup.fsms) == 0


class TestSupervisorHealth:
    @pytest.mark.asyncio
    async def test_supervisor_detects_stuck_fsm(self):
        sup = GlobalSupervisor(stuck_timeout_seconds=0)  # immediate for test
        fsm = PositionFSM(symbol="BTCUSDT", side="Sell")
        fsm.transition(FSMState.PREPARING, trigger="test", reason="test")
        sup.register_fsm(fsm)

        # Manually set stale timestamp
        sup._last_event_ts["BTCUSDT_Sell"] = 0
        issues = await sup.check_health()

        assert len(issues) > 0
        assert any("stuck" in i.lower() for i in issues)

    @pytest.mark.asyncio
    async def test_all_healthy_when_active(self):
        sup = GlobalSupervisor(stuck_timeout_seconds=9999)
        fsm = PositionFSM(symbol="BTCUSDT", side="Sell")
        sup.register_fsm(fsm)
        sup.touch("BTCUSDT_Sell")

        issues = await sup.check_health()
        assert len(issues) == 0


class TestSupervisorRiskLimit:
    def test_risk_limit_hit_changes_supervisor_state(self):
        sup = GlobalSupervisor()
        event = RiskLimitHit(limit_type="daily_loss", symbol="BTCUSDT",
                             current_value=-150.0, threshold=100.0)

        sup.handle_risk_limit(event)

        assert sup.state == SupervisorState.RISK_LIMITED
        assert "daily_loss" in sup.active_limits

    def test_multiple_risk_limits(self):
        sup = GlobalSupervisor()
        sup.handle_risk_limit(RiskLimitHit(limit_type="daily_loss", symbol="BTCUSDT",
                                            current_value=-150.0, threshold=100.0))
        sup.handle_risk_limit(RiskLimitHit(limit_type="drawdown", symbol="*",
                                            current_value=-500.0, threshold=400.0))

        assert sup.state == SupervisorState.RISK_LIMITED
        assert len(sup.active_limits) == 2


class TestSupervisorFsmKey:
    def test_fsm_key_generation(self):
        sup = GlobalSupervisor()
        assert sup._fsm_key("BTCUSDT", "Sell") == "BTCUSDT_Sell"
        assert sup._fsm_key("ETHUSDT", "Buy") == "ETHUSDT_Buy"
