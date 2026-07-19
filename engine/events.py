"""Event type definitions for the trading engine EventBus."""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto


class EventType(Enum):
    PRICE_UPDATE = auto()
    ORDER_FILLED = auto()
    ORDER_REJECTED = auto()
    ORDER_CANCELLED = auto()
    POSITION_CHANGED = auto()
    FUNDING_CHANGED = auto()
    AI_COMPLETED = auto()
    TIMER_TICK = auto()
    RISK_LIMIT_HIT = auto()
    USER_COMMAND = auto()
    SYSTEM_SHUTDOWN = auto()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uid() -> str:
    return uuid.uuid4().hex


@dataclass
class Event:
    """Base event. All events have a unique ID, type, and timestamp."""
    type: EventType = field(init=False)
    event_id: str = field(default_factory=_uid)
    timestamp: datetime = field(default_factory=_now)


@dataclass
class PriceUpdate(Event):
    symbol: str = ""
    price: float = 0.0
    high: float = 0.0
    low: float = 0.0
    volume: float = 0.0

    def __post_init__(self):
        self.type = EventType.PRICE_UPDATE


@dataclass
class OrderFilled(Event):
    order_id: str = ""
    order_link_id: str = ""
    symbol: str = ""
    side: str = ""
    qty: float = 0.0
    price: float = 0.0

    def __post_init__(self):
        self.type = EventType.ORDER_FILLED


@dataclass
class OrderRejected(Event):
    order_id: str = ""
    order_link_id: str = ""
    symbol: str = ""
    reason: str = ""

    def __post_init__(self):
        self.type = EventType.ORDER_REJECTED


@dataclass
class OrderCancelled(Event):
    order_id: str = ""
    symbol: str = ""

    def __post_init__(self):
        self.type = EventType.ORDER_CANCELLED


@dataclass
class PositionChanged(Event):
    """Primary source of truth. Exchange position state."""
    symbol: str = ""
    side: str = ""
    size: float = 0.0
    margin: float = 0.0
    unrealised_pnl: float = 0.0
    roe_percent: float = 0.0
    liq_price: float = 0.0

    def __post_init__(self):
        self.type = EventType.POSITION_CHANGED


@dataclass
class FundingChanged(Event):
    symbol: str = ""
    rate: float = 0.0

    def __post_init__(self):
        self.type = EventType.FUNDING_CHANGED


@dataclass
class AICompleted(Event):
    decision: dict = field(default_factory=dict)
    operation_id: str = ""
    state_version: int = 0

    def __post_init__(self):
        self.type = EventType.AI_COMPLETED


@dataclass
class TimerTick(Event):
    def __post_init__(self):
        self.type = EventType.TIMER_TICK


@dataclass
class RiskLimitHit(Event):
    limit_type: str = ""      # "daily_loss", "drawdown", "position_margin"
    symbol: str = ""
    current_value: float = 0.0
    threshold: float = 0.0

    def __post_init__(self):
        self.type = EventType.RISK_LIMIT_HIT


@dataclass
class UserCommand(Event):
    command: str = ""          # "pause", "resume", "close", "status"
    symbol: str = ""
    params: dict = field(default_factory=dict)

    def __post_init__(self):
        self.type = EventType.USER_COMMAND


@dataclass
class SystemShutdown(Event):
    reason: str = ""

    def __post_init__(self):
        self.type = EventType.SYSTEM_SHUTDOWN
