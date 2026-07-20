"""StateSnapshotter — save ExchangeState snapshots every N events."""
import json
import logging

log = logging.getLogger(__name__)


class StateSnapshotter:
    """Periodically saves ExchangeState snapshots for fast recovery."""

    def __init__(self, state, snap_path: str, interval: int = 100):
        self._state = state
        self._snap_path = snap_path
        self._interval = interval
        self._counter = 0

    def on_event(self) -> None:
        self._counter += 1
        if self._counter % self._interval == 0:
            self._save()

    def _save(self) -> None:
        with open(self._snap_path, "w") as f:
            json.dump(self._state.snapshot(), f, indent=2)
        log.debug("Snapshot saved at version %d", self._state.version)
