from dataclasses import dataclass
from domain.events.base import Event, EventType


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
