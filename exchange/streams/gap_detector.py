"""GapDetector — per-stream sequence gap detection."""
import logging

log = logging.getLogger(__name__)


class GapDetector:
    """Detects gaps in message sequence numbers. Triggers REST resync."""

    def __init__(self, max_gap: int = 5):
        self._last_seq = 0
        self._max_gap = max_gap

    def check(self, raw_msg: dict) -> bool:
        seq = raw_msg.get("seq", 0)
        if not isinstance(seq, int) or seq == 0:
            return False  # no sequence tracking for this message
        gap = seq - self._last_seq > 1
        self._last_seq = max(self._last_seq, seq)
        if gap:
            log.warning("Sequence gap: %d → %d", self._last_seq, seq)
        return gap

    def reset(self) -> None:
        self._last_seq = 0
