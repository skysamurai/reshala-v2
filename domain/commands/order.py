"""OrderCommand — contract between FSM and ExchangeAdapter."""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class OrderCommand:
    """FSM emits this. ExchangeAdapter executes it. No Bybit knowledge here."""
    symbol: str
    side: str              # "Buy" | "Sell"
    qty: str               # already rounded to exchange step
    price: str = ""        # "" = Market order
    reduce_only: bool = False
    operation_id: str = ""  # FSM operation UUID
    order_link_id: str = "" # idempotency key
    sequence: int = 0       # seq within operation
    tp_price: str = ""
    sl_price: str = ""
    correlation_id: str = "" # AI → Order → Fill → TP → Close chain
    created_at: datetime = field(default_factory=datetime.now)
