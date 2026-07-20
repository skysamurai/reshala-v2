"""Base event types."""
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
    HEALTH_EVENT = auto()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uid() -> str:
    return uuid.uuid4().hex


@dataclass
class Event:
    type: EventType = field(init=False)
    event_id: str = field(default_factory=_uid)
    timestamp: datetime = field(default_factory=_now)
    correlation_id: str = ""
    sequence: int = 0
    source: str = ""
