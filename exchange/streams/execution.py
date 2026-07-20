"""ExecutionStream — OrderFilled producer. Priority ⭐⭐⭐⭐⭐ (never drop)."""
from exchange.streams.base import BaseStream
from exchange.mapper import to_order_filled


class ExecutionStream(BaseStream):
    @property
    def topic_prefix(self) -> str:
        return "execution"

    def map_event(self, raw: dict):
        return to_order_filled(raw)
