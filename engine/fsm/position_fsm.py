"""PositionFSM — per-symbol finite state machine for trading control."""
import logging
from typing import Optional
from engine.fsm.states import (
    FSMState, ActiveSubState, WaitReason, TransitionTable,
)

log = logging.getLogger(__name__)


class PositionFSM:
    """Finite State Machine for one trading position.

    Each losing position gets its own FSM instance. The FSM validates
    every transition against the deterministic TransitionTable and
    increments state_version on each successful transition.

    Key invariants:
    - State + Event = Next State (deterministic)
    - Exchange is the single source of truth
    - AI never changes state directly — it proposes, FSM validates
    - state_version prevents stale decision execution
    """

    def __init__(
        self,
        symbol: str,
        side: str,
        initial_state: FSMState = FSMState.IDLE,
    ):
        self.symbol = symbol
        self.side = side

        self.state: FSMState = initial_state
        self.active_substate: ActiveSubState = TransitionTable.default_substate(initial_state)
        self.wait_reason: Optional[WaitReason] = None
        self.wait_until: float = 0.0

        self.state_version: int = 0
        self.operation_id: Optional[str] = None  # current operation UUID

        # Order tracking for idempotency
        self._order_seq: int = 0
        self._pending_order_link_ids: set[str] = set()

        # Transition history (last N for diagnostics)
        self._history: list[dict] = []

    # ─── Transition ───────────────────────────────────────

    def transition(
        self,
        to_state: FSMState,
        trigger: str,
        reason: str,
        wait_reason: Optional[WaitReason] = None,
        wait_until: float = 0.0,
        operation_id: Optional[str] = None,
        order_link_id: Optional[str] = None,
    ) -> bool:
        """Attempt a state transition. Returns True if allowed and executed."""
        if not TransitionTable.is_allowed(self.state, to_state):
            log.warning(
                "%s: invalid transition %s → %s (trigger=%s)",
                self.symbol, self.state.value, to_state.value, trigger,
            )
            return False

        old_state = self.state
        self.state = to_state
        self.state_version += 1

        if to_state == FSMState.WAITING:
            self.wait_reason = wait_reason
            self.wait_until = wait_until
        else:
            self.wait_reason = None
            self.wait_until = 0.0

        if to_state == FSMState.ACTIVE:
            self.active_substate = TransitionTable.default_substate(to_state)
        elif to_state == FSMState.IDLE:
            self.active_substate = ActiveSubState.MONITORING
            self._order_seq = 0
            self.operation_id = None

        if operation_id:
            self.operation_id = operation_id
        if order_link_id:
            self._pending_order_link_ids.add(order_link_id)

        self._history.append({
            "from": old_state.value,
            "to": to_state.value,
            "trigger": trigger,
            "version": self.state_version,
        })
        # Keep last 100 transitions
        if len(self._history) > 100:
            self._history = self._history[-100:]

        log.info(
            "%s v%d: %s → %s (%s)",
            self.symbol, self.state_version,
            old_state.value, to_state.value, trigger,
        )
        return True

    # ─── Sub-state ────────────────────────────────────────

    def set_substate(self, substate: ActiveSubState) -> bool:
        """Set the active sub-state. Only valid when in ACTIVE."""
        if self.state != FSMState.ACTIVE:
            log.warning("%s: cannot set sub-state when in %s", self.symbol, self.state.value)
            return False
        self.active_substate = substate
        log.debug("%s: sub-state → %s", self.symbol, substate.value)
        return True

    # ─── State version check ──────────────────────────────

    def is_current_version(self, version: int) -> bool:
        """Check if a version matches the current FSM version."""
        return version == self.state_version

    # ─── Order sequence ───────────────────────────────────

    def next_order_seq(self) -> int:
        """Increment and return the next order sequence number."""
        self._order_seq += 1
        return self._order_seq

    @property
    def current_seq(self) -> int:
        return self._order_seq

    # ─── Status ───────────────────────────────────────────

    def is_active(self) -> bool:
        """Is the FSM in a state where it can process trading events?"""
        return self.state not in {
            FSMState.SHUTDOWN,
            FSMState.ERROR,
            FSMState.PAUSED_MANUAL,
            FSMState.PAUSED_RISK,
            FSMState.PAUSED_API,
            FSMState.PAUSED_EXCHANGE,
        }

    def is_trading(self) -> bool:
        """Is the FSM actively trading (not paused/errored/waiting)?"""
        return self.state in {
            FSMState.IDLE, FSMState.PREPARING, FSMState.SENDING_ORDER,
            FSMState.VERIFY, FSMState.WAIT_FILL, FSMState.ACTIVE,
            FSMState.CLOSING,
        }

    def summary(self) -> dict:
        """Return a diagnostic summary of the FSM state."""
        return {
            "symbol": self.symbol,
            "side": self.side,
            "state": self.state.value,
            "active_substate": self.active_substate.value,
            "wait_reason": self.wait_reason.value if self.wait_reason else None,
            "state_version": self.state_version,
            "operation_id": self.operation_id,
            "order_seq": self._order_seq,
        }
