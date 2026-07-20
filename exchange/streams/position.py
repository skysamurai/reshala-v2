"""PositionStream — PositionChanged producer. Priority ⭐⭐⭐⭐⭐ (never drop)."""
from exchange.streams.base import BaseStream
from exchange.mapper import to_position_changed


class PositionStream(BaseStream):
    @property
    def topic_prefix(self) -> str:
        return "position"

    def map_event(self, raw: dict):
        return to_position_changed(raw)
