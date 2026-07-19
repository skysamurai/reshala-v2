"""FSM state and sub-state enums for PositionFSM."""
from enum import Enum
from typing import FrozenSet


class FSMState(Enum):
    """Top-level states of a PositionFSM."""
    IDLE = "idle"
    PREPARING = "preparing"
    SENDING_ORDER = "sending_order"
    VERIFY = "verify"
    WAIT_FILL = "wait_fill"
    ACTIVE = "active"
    CLOSING = "closing"
    WAITING = "waiting"
    ERROR = "error"
    PAUSED_MANUAL = "paused_manual"
    PAUSED_RISK = "paused_risk"
    PAUSED_API = "paused_api"
    PAUSED_EXCHANGE = "paused_exchange"
    SHUTDOWN = "shutdown"
    RECOVERING = "recovering"


class ActiveSubState(Enum):
    """Sub-states within ACTIVE."""
    MONITORING = "monitoring"
    DCA = "dca"
    HEDGE = "hedge"
    SCALPING = "scalping"
    EXITING = "exiting"


class WaitReason(Enum):
    """Reasons for WAITING state."""
    WAIT_AI = "wait_ai"
    WAIT_MARKET = "wait_market"
    WAIT_COOLDOWN = "wait_cooldown"
    WAIT_RETRY = "wait_retry"


class TransitionTable:
    """Deterministic transition table for PositionFSM.

    State + Event = Next State. Nothing else.

    Usage:
        TransitionTable.is_allowed(from_state, to_state) -> bool
        TransitionTable.get_allowed_exits(state) -> FrozenSet[FSMState]
    """

    _transitions: dict[FSMState, FrozenSet[FSMState]] = {
        FSMState.IDLE: frozenset({
            FSMState.PREPARING,
            FSMState.WAITING,
            FSMState.CLOSING,
            FSMState.ERROR,
            FSMState.PAUSED_MANUAL,
            FSMState.PAUSED_RISK,
            FSMState.PAUSED_API,
            FSMState.PAUSED_EXCHANGE,
            FSMState.SHUTDOWN,
        }),
        FSMState.PREPARING: frozenset({
            FSMState.SENDING_ORDER,
            FSMState.WAITING,
            FSMState.IDLE,
            FSMState.ERROR,
            FSMState.PAUSED_MANUAL,
            FSMState.PAUSED_RISK,
            FSMState.PAUSED_API,
            FSMState.PAUSED_EXCHANGE,
            FSMState.SHUTDOWN,
        }),
        FSMState.SENDING_ORDER: frozenset({
            FSMState.VERIFY,
            FSMState.ERROR,
            FSMState.PAUSED_MANUAL,
            FSMState.PAUSED_RISK,
            FSMState.PAUSED_API,
            FSMState.PAUSED_EXCHANGE,
            FSMState.SHUTDOWN,
        }),
        FSMState.VERIFY: frozenset({
            FSMState.WAIT_FILL,
            FSMState.WAITING,
            FSMState.IDLE,
            FSMState.ERROR,
            FSMState.PAUSED_MANUAL,
            FSMState.PAUSED_RISK,
            FSMState.PAUSED_API,
            FSMState.PAUSED_EXCHANGE,
            FSMState.SHUTDOWN,
        }),
        FSMState.WAIT_FILL: frozenset({
            FSMState.ACTIVE,
            FSMState.VERIFY,
            FSMState.ERROR,
            FSMState.PAUSED_MANUAL,
            FSMState.PAUSED_RISK,
            FSMState.PAUSED_API,
            FSMState.PAUSED_EXCHANGE,
            FSMState.SHUTDOWN,
        }),
        FSMState.ACTIVE: frozenset({
            FSMState.CLOSING,
            FSMState.WAITING,
            FSMState.IDLE,
            FSMState.ERROR,
            FSMState.PAUSED_MANUAL,
            FSMState.PAUSED_RISK,
            FSMState.PAUSED_API,
            FSMState.PAUSED_EXCHANGE,
            FSMState.SHUTDOWN,
        }),
        FSMState.CLOSING: frozenset({
            FSMState.IDLE,
            FSMState.ERROR,
            FSMState.PAUSED_MANUAL,
            FSMState.PAUSED_RISK,
            FSMState.PAUSED_API,
            FSMState.PAUSED_EXCHANGE,
            FSMState.SHUTDOWN,
        }),
        FSMState.WAITING: frozenset({
            FSMState.IDLE,
            FSMState.PREPARING,
            FSMState.ERROR,
            FSMState.PAUSED_MANUAL,
            FSMState.PAUSED_RISK,
            FSMState.PAUSED_API,
            FSMState.PAUSED_EXCHANGE,
            FSMState.SHUTDOWN,
        }),
        FSMState.ERROR: frozenset({
            FSMState.RECOVERING,
            FSMState.IDLE,
            FSMState.PAUSED_MANUAL,
            FSMState.SHUTDOWN,
        }),
        FSMState.PAUSED_MANUAL: frozenset({
            FSMState.IDLE,
            FSMState.SHUTDOWN,
        }),
        FSMState.PAUSED_RISK: frozenset({
            FSMState.IDLE,
            FSMState.SHUTDOWN,
        }),
        FSMState.PAUSED_API: frozenset({
            FSMState.RECOVERING,
            FSMState.SHUTDOWN,
        }),
        FSMState.PAUSED_EXCHANGE: frozenset({
            FSMState.RECOVERING,
            FSMState.SHUTDOWN,
        }),
        FSMState.RECOVERING: frozenset({
            FSMState.IDLE,
            FSMState.ERROR,
            FSMState.SHUTDOWN,
        }),
        FSMState.SHUTDOWN: frozenset(),
    }

    _default_substates: dict[FSMState, ActiveSubState] = {
        FSMState.ACTIVE: ActiveSubState.MONITORING,
    }

    @classmethod
    def is_allowed(cls, from_state: FSMState, to_state: FSMState) -> bool:
        if from_state not in cls._transitions:
            return False
        return to_state in cls._transitions[from_state]

    @classmethod
    def get_allowed_exits(cls, state: FSMState) -> FrozenSet[FSMState]:
        return cls._transitions.get(state, frozenset())

    @classmethod
    def default_substate(cls, state: FSMState) -> ActiveSubState:
        return cls._default_substates.get(state, ActiveSubState.MONITORING)
