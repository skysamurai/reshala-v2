"""CancelCommand — cancel an open order."""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CancelCommand:
    symbol: str
    order_id: str = ""
    order_link_id: str = ""
    operation_id: str = ""
    sequence: int = 0
    correlation_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)
