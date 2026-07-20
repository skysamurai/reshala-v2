from dataclasses import dataclass
from domain.events.base import Event, EventType


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
