"""FSM state and sub-state enums for PositionFSM."""
from enum import Enum


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
