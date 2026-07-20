"""EventLogger — JSONL append-only black box for all FSM transitions."""
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from domain.fsm.states import FSMState


class EventLogger:
    """Append-only JSONL logger for FSM state transitions.

    Each transition writes one JSON line with event_id, timestamp,
    state version, symbol, and transition details.
    """

    def __init__(self, log_path: str, max_file_size_mb: int = 100):
        os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
        self._path = log_path
        self._max_bytes = max_file_size_mb * 1024 * 1024
        self._file = None

    async def _ensure_open(self) -> None:
        if self._file is None:
            self._file = open(self._path, "a", encoding="utf-8")

    async def log_transition(
        self,
        symbol: str,
        from_state: FSMState,
        to_state: FSMState,
        trigger: str,
        reason: str,
        operation_id: Optional[str] = None,
        order_link_id: Optional[str] = None,
        state_version: int = 0,
        extra: Optional[dict] = None,
    ) -> None:
        await self._ensure_open()

        entry = {
            "event_id": uuid.uuid4().hex[:12],
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "state_version": state_version,
            "symbol": symbol,
            "from_state": from_state.value,
            "to_state": to_state.value,
            "trigger": trigger,
            "reason": reason,
            "operation_id": operation_id,
            "order_link_id": order_link_id,
            "extra": extra or {},
        }

        self._file.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._file.flush()

        if self._file.tell() > self._max_bytes:
            await self._rotate()

    async def _rotate(self) -> None:
        if self._file:
            self._file.close()
        log_dir = os.path.dirname(self._path) or "."
        base_name = os.path.basename(self._path)
        name, ext = os.path.splitext(base_name)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        i = 1
        while True:
            new_name = f"{name}_{date_str}_{i}{ext}"
            self._path = os.path.join(log_dir, new_name)
            if not os.path.exists(self._path):
                break
            i += 1
        self._file = open(self._path, "a", encoding="utf-8")

    async def close(self) -> None:
        if self._file:
            self._file.close()
            self._file = None
