"""ReplayEngine — restore ExchangeState from snapshot + event log."""
import json
import logging

log = logging.getLogger(__name__)


class ReplayEngine:
    """Reconstruct ExchangeState from snapshot + JSONL event log.

    Uses EventSerializer for consistent ser/deser (avoids manual JSON parsing).
    Will be wired to ExchangeState in Phase 2.
    """

    def __init__(self):
        self._serializer = None  # EventSerializer — wired in Phase 2

    def replay(self, snap_path: str, log_path: str):
        """Replay snapshot + event log into an ExchangeState."""
        with open(snap_path) as f:
            snap = json.load(f)

        # Phase 2: import ExchangeState and EventSerializer
        from domain.exchange_state import ExchangeState
        from domain.events.serialization import EventSerializer
        self._serializer = EventSerializer()

        state = ExchangeState.from_snapshot(snap)

        try:
            events = 0
            with open(log_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    event = self._serializer.from_json(line)
                    state.apply(event)
                    events += 1
            log.info("Replay: restored v%d from snapshot + %d events",
                     state.version, events)
        except FileNotFoundError:
            pass

        return state
