"""Tests for PositionFSM — per-symbol state machine."""
import pytest
from engine.fsm.position_fsm import PositionFSM
from engine.fsm.states import FSMState, ActiveSubState, WaitReason


class TestPositionFSMCreation:
    def test_new_fsm_starts_in_idle(self):
        fsm = PositionFSM(symbol="BTCUSDT", side="Sell")
        assert fsm.symbol == "BTCUSDT"
        assert fsm.side == "Sell"
        assert fsm.state == FSMState.IDLE
        assert fsm.state_version == 0

    def test_new_fsm_custom_initial_state(self):
        fsm = PositionFSM(symbol="ETHUSDT", side="Buy", initial_state=FSMState.RECOVERING)
        assert fsm.state == FSMState.RECOVERING


class TestPositionFSMTransitions:
    def test_valid_transition_idle_to_preparing(self):
        fsm = PositionFSM(symbol="BTCUSDT", side="Sell")
        result = fsm.transition(FSMState.PREPARING, trigger="AICompleted", reason="AI chose DCA")
        assert result is True
        assert fsm.state == FSMState.PREPARING
        assert fsm.state_version == 1

    def test_invalid_transition_returns_false(self):
        fsm = PositionFSM(symbol="BTCUSDT", side="Sell")
        # IDLE → SENDING_ORDER not allowed (must go through PREPARING)
        result = fsm.transition(FSMState.SENDING_ORDER, trigger="AICompleted", reason="skip")
        assert result is False
        assert fsm.state == FSMState.IDLE  # unchanged
        assert fsm.state_version == 0      # unchanged

    def test_state_version_increments_on_each_transition(self):
        fsm = PositionFSM(symbol="BTCUSDT", side="Sell")
        assert fsm.state_version == 0

        fsm.transition(FSMState.PREPARING, trigger="tick", reason="1")
        assert fsm.state_version == 1

        fsm.transition(FSMState.SENDING_ORDER, trigger="tick", reason="2")
        assert fsm.state_version == 2

        fsm.transition(FSMState.VERIFY, trigger="tick", reason="3")
        assert fsm.state_version == 3

    def test_transition_to_error_from_any_valid_state(self):
        for state in [FSMState.IDLE, FSMState.PREPARING, FSMState.SENDING_ORDER,
                       FSMState.VERIFY, FSMState.WAIT_FILL, FSMState.ACTIVE]:
            fsm = PositionFSM(symbol="BTCUSDT", side="Sell", initial_state=state)
            result = fsm.transition(FSMState.ERROR, trigger="exception", reason="API timeout")
            assert result is True, f"Transition {state} → ERROR should be allowed"
            assert fsm.state == FSMState.ERROR

    def test_full_happy_path(self):
        """Test the full IDLE → ... → ACTIVE → CLOSING → IDLE cycle."""
        fsm = PositionFSM(symbol="BTCUSDT", side="Sell")

        path = [
            (FSMState.PREPARING, "AICompleted", "AI chose DCA"),
            (FSMState.SENDING_ORDER, "OrderReady", "order params valid"),
            (FSMState.VERIFY, "OrderSent", "placed on exchange"),
            (FSMState.WAIT_FILL, "OrderConfirmed", "order accepted"),
            (FSMState.ACTIVE, "OrderFilled", "DCA filled"),
            (FSMState.CLOSING, "RecoveryComplete", "position recovered"),
            (FSMState.IDLE, "PositionClosed", "closed"),
        ]

        for i, (to_state, trigger, reason) in enumerate(path):
            result = fsm.transition(to_state, trigger=trigger, reason=reason)
            assert result is True, f"Step {i}: {fsm.state.value} → {to_state.value} failed"
            assert fsm.state == to_state, f"Step {i}: expected {to_state.value}, got {fsm.state.value}"


class TestActiveSubStates:
    def test_default_substate_on_enter_active(self):
        fsm = PositionFSM(symbol="BTCUSDT", side="Sell", initial_state=FSMState.WAIT_FILL)
        fsm.transition(FSMState.ACTIVE, trigger="OrderFilled", reason="filled")
        assert fsm.active_substate == ActiveSubState.MONITORING

    def test_set_substate(self):
        fsm = PositionFSM(symbol="BTCUSDT", side="Sell", initial_state=FSMState.ACTIVE)
        fsm.set_substate(ActiveSubState.DCA)
        assert fsm.active_substate == ActiveSubState.DCA

    def test_cannot_set_substate_when_not_active(self):
        fsm = PositionFSM(symbol="BTCUSDT", side="Sell", initial_state=FSMState.IDLE)
        fsm.set_substate(ActiveSubState.DCA)
        assert fsm.active_substate == ActiveSubState.MONITORING  # unchanged


class TestWaiting:
    def test_waiting_stores_reason(self):
        fsm = PositionFSM(symbol="BTCUSDT", side="Sell")
        fsm.transition(FSMState.WAITING, trigger="SafetyGuard", reason="funding window",
                       wait_reason=WaitReason.WAIT_MARKET)
        assert fsm.state == FSMState.WAITING
        assert fsm.wait_reason == WaitReason.WAIT_MARKET

    def test_waiting_stores_until_timestamp(self):
        fsm = PositionFSM(symbol="BTCUSDT", side="Sell")
        fsm.transition(FSMState.WAITING, trigger="Cooldown", reason="2 min between orders",
                       wait_reason=WaitReason.WAIT_COOLDOWN, wait_until=900.0)
        assert fsm.wait_until == 900.0


class TestStaleDecision:
    def test_is_current_version(self):
        fsm = PositionFSM(symbol="BTCUSDT", side="Sell")
        fsm.transition(FSMState.PREPARING, trigger="tick", reason="1")  # v=1
        fsm.transition(FSMState.SENDING_ORDER, trigger="tick", reason="2")  # v=2
        fsm.transition(FSMState.VERIFY, trigger="tick", reason="3")  # v=3

        assert fsm.is_current_version(3) is True
        assert fsm.is_current_version(2) is False   # stale
        assert fsm.is_current_version(1) is False   # stale
