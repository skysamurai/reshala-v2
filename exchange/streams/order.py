"""OrderStream — OrderRejected/OrderCancelled producer. Priority ⭐⭐⭐⭐."""
from exchange.streams.base import BaseStream
from exchange.mapper import to_order_rejected, to_order_cancelled


class OrderStream(BaseStream):
    @property
    def topic_prefix(self) -> str:
        return "order"

    def map_event(self, raw: dict):
        status = raw.get("orderStatus", raw.get("status", ""))
        if status in ("Rejected", "rejected"):
            return to_order_rejected(raw)
        if status in ("Cancelled", "cancelled"):
            return to_order_cancelled(raw)
        return None  # ignore New/PartiallyFilled/Filled — ExecutionStream handles fills
