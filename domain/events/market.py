from dataclasses import dataclass
from domain.events.base import Event, EventType


@dataclass
class PriceUpdate(Event):
    symbol: str = ""
    price: float = 0.0
    high: float = 0.0
    low: float = 0.0
    volume: float = 0.0

    def __post_init__(self):
        self.type = EventType.PRICE_UPDATE
