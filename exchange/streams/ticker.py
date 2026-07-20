"""TickerStream — PriceUpdate producer. Priority ⭐⭐⭐ (can coalesce)."""
from exchange.streams.base import BaseStream
from exchange.mapper import to_price_update


class TickerStream(BaseStream):
    @property
    def topic_prefix(self) -> str:
        return "tickers"

    def map_event(self, raw: dict):
        return to_price_update(raw)
