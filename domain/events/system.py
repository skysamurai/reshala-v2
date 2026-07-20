from dataclasses import dataclass, field
from domain.events.base import Event, EventType


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


@dataclass
class HealthEvent(Event):
    severity: str = ""   # "warning" | "critical"
    component: str = ""  # "ticker_stream" | "position_stream" | "api"
    message: str = ""

    def __post_init__(self):
        self.type = EventType.HEALTH_EVENT
