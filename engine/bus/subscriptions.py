"""Subscription routing and Dead Letter Queue."""
import json
import logging
from domain.events.base import Event

log = logging.getLogger(__name__)


class DeadLetterQueue:
    """Events that cannot be processed (FSM removed, corrupted data, unknown symbol)."""

    def __init__(self, log_path: str = "logs/dead_letter.jsonl"):
        self._path = log_path

    async def push(self, event: Event, error: str) -> None:
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "event_id": event.event_id,
                "type": event.type.name,
                "symbol": getattr(event, "symbol", ""),
                "error": error,
            }, ensure_ascii=False) + "\n")
        log.debug("DLQ: %s %s — %s", event.type.name, getattr(event, "symbol", ""), error)
