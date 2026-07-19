"""Tests for FSM transition validation."""
import pytest
from engine.fsm.states import FSMState, TransitionTable, ActiveSubState


class TestTransitionTable:
    def test_valid_transition_idle_to_preparing(self):
        assert TransitionTable.is_allowed(FSMState.IDLE, FSMState.PREPARING)

    def test_valid_transition_preparing_to_sending_order(self):
        assert TransitionTable.is_allowed(FSMState.PREPARING, FSMState.SENDING_ORDER)

    def test_valid_transition_sending_order_to_verify(self):
        assert TransitionTable.is_allowed(FSMState.SENDING_ORDER, FSMState.VERIFY)

    def test_valid_transition_verify_to_wait_fill(self):
        assert TransitionTable.is_allowed(FSMState.VERIFY, FSMState.WAIT_FILL)

    def test_valid_transition_wait_fill_to_active(self):
        assert TransitionTable.is_allowed(FSMState.WAIT_FILL, FSMState.ACTIVE)

    def test_valid_transition_active_to_closing(self):
        assert TransitionTable.is_allowed(FSMState.ACTIVE, FSMState.CLOSING)

    def test_valid_transition_closing_to_idle(self):
        assert TransitionTable.is_allowed(FSMState.CLOSING, FSMState.IDLE)

    def test_any_state_to_error(self):
        # SHUTDOWN is terminal (no exits). PAUSED_MANUAL and PAUSED_RISK
        # only allow IDLE/SHUTDOWN exits. PAUSED_API and PAUSED_EXCHANGE
        # only allow RECOVERING/SHUTDOWN. None can transition to ERROR.
        error_blocked = {
            FSMState.SHUTDOWN, FSMState.PAUSED_MANUAL, FSMState.PAUSED_RISK,
            FSMState.PAUSED_API, FSMState.PAUSED_EXCHANGE,
        }
        for state in FSMState:
            if state not in error_blocked and state != FSMState.ERROR:
                assert TransitionTable.is_allowed(state, FSMState.ERROR)

    def test_any_state_to_paused(self):
        paused_states = [FSMState.PAUSED_MANUAL, FSMState.PAUSED_RISK,
                         FSMState.PAUSED_API, FSMState.PAUSED_EXCHANGE]
        # SHUTDOWN is terminal. ERROR only allows PAUSED_MANUAL (not the others).
        for state in FSMState:
            if state not in [FSMState.SHUTDOWN] + paused_states:
                allowed_paused = TransitionTable.get_allowed_exits(state) & set(paused_states)
                for paused in allowed_paused:
                    assert TransitionTable.is_allowed(state, paused)

    def test_idle_to_sending_order_not_allowed(self):
        assert not TransitionTable.is_allowed(FSMState.IDLE, FSMState.SENDING_ORDER)

    def test_waiting_to_waiting_not_allowed(self):
        """WAITING → WAITING is not a transition (no state change)."""
        assert not TransitionTable.is_allowed(FSMState.WAITING, FSMState.WAITING)

    def test_shutdown_is_terminal(self):
        for state in FSMState:
            if state != FSMState.SHUTDOWN:
                assert not TransitionTable.is_allowed(FSMState.SHUTDOWN, state)

    def test_recovering_to_idle_allowed(self):
        assert TransitionTable.is_allowed(FSMState.RECOVERING, FSMState.IDLE)

    def test_recovering_to_error_allowed(self):
        assert TransitionTable.is_allowed(FSMState.RECOVERING, FSMState.ERROR)

    def test_error_to_idle_allowed(self):
        assert TransitionTable.is_allowed(FSMState.ERROR, FSMState.IDLE)

    def test_active_substate_default_is_monitoring(self):
        assert TransitionTable.default_substate(FSMState.ACTIVE) == ActiveSubState.MONITORING

    def test_get_allowed_exits(self):
        exits = TransitionTable.get_allowed_exits(FSMState.IDLE)
        assert FSMState.PREPARING in exits
        assert FSMState.WAITING in exits
        assert FSMState.ERROR in exits
        assert FSMState.CLOSING in exits
        assert FSMState.SENDING_ORDER not in exits
