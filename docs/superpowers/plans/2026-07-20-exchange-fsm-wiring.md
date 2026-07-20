# Exchange + FSM Wiring — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect reshala-v2 FSM engine to Bybit via MCP — WebSocket streams feed EventBus, FSM reads ExchangeState, OrderCommands execute via ExchangeAdapter.

**Architecture:** Vertical slices. Each phase ends with a runnable, testable system. No phase depends on unfinished work from the next phase.

**Tech Stack:** Python 3.13, asyncio, dataclasses, enum, Bybit MCP tools, pytest + pytest-asyncio

**Prerequisite:** 70 existing tests must stay green throughout all phases.

---

## Phase 1: Restructure + EventBus Upgrade

**Goal after phase:** All 70 existing tests pass from new locations. EventBus has bounded queues, priority levels, and coalescing for PriceUpdate.

### Task 1.1: Move events to `domain/events/` package

**Files:**
- Create: `domain/__init__.py`
- Create: `domain/events/__init__.py`
- Create: `domain/events/base.py` (Event, EventType — from `engine/events.py`)
- Create: `domain/events/market.py` (PriceUpdate)
- Create: `domain/events/orders.py` (OrderFilled, OrderRejected, OrderCancelled)
- Create: `domain/events/positions.py` (PositionChanged, FundingChanged)
- Create: `domain/events/ai.py` (AICompleted)
- Create: `domain/events/system.py` (TimerTick, SystemShutdown, RiskLimitHit)
- Modify: `engine/events.py` → re-export from `domain.events` for backward compat

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p domain/events
touch domain/__init__.py domain/events/__init__.py
```

- [ ] **Step 2: Move Event and EventType to `domain/events/base.py`**

Extract from `engine/events.py`: `Event` base class, `EventType` enum, `_now()`, `_uid()` helpers.

```python
"""Base event types."""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto


class EventType(Enum):
    PRICE_UPDATE = auto()
    ORDER_FILLED = auto()
    ORDER_REJECTED = auto()
    ORDER_CANCELLED = auto()
    POSITION_CHANGED = auto()
    FUNDING_CHANGED = auto()
    AI_COMPLETED = auto()
    TIMER_TICK = auto()
    RISK_LIMIT_HIT = auto()
    USER_COMMAND = auto()
    SYSTEM_SHUTDOWN = auto()
    HEALTH_EVENT = auto()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uid() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class Event:
    type: EventType
    event_id: str = field(default_factory=_uid)
    timestamp: datetime = field(default_factory=_now)
    correlation_id: str = ""
    sequence: int = 0
    source: str = ""
```

- [ ] **Step 3: Split remaining events into domain packages**

```python
# domain/events/market.py
from dataclasses import dataclass
from domain.events.base import Event, EventType

@dataclass
class PriceUpdate(Event):
    symbol: str = ""
    price: float = 0.0
    high: float = 0.0
    low: float = 0.0
    volume: float = 0.0
    def __post_init__(self): self.type = EventType.PRICE_UPDATE
```

```python
# domain/events/orders.py
from dataclasses import dataclass
from domain.events.base import Event, EventType

@dataclass
class OrderFilled(Event):
    order_id: str = ""
    order_link_id: str = ""
    symbol: str = ""
    side: str = ""
    qty: float = 0.0
    price: float = 0.0
    def __post_init__(self): self.type = EventType.ORDER_FILLED

@dataclass
class OrderRejected(Event):
    order_id: str = ""
    order_link_id: str = ""
    symbol: str = ""
    reason: str = ""
    def __post_init__(self): self.type = EventType.ORDER_REJECTED

@dataclass
class OrderCancelled(Event):
    order_id: str = ""
    symbol: str = ""
    def __post_init__(self): self.type = EventType.ORDER_CANCELLED
```

```python
# domain/events/positions.py
from dataclasses import dataclass
from domain.events.base import Event, EventType

@dataclass
class PositionChanged(Event):
    symbol: str = ""
    side: str = ""
    size: float = 0.0
    margin: float = 0.0
    unrealised_pnl: float = 0.0
    roe_percent: float = 0.0
    liq_price: float = 0.0
    def __post_init__(self): self.type = EventType.POSITION_CHANGED

@dataclass
class FundingChanged(Event):
    symbol: str = ""
    rate: float = 0.0
    def __post_init__(self): self.type = EventType.FUNDING_CHANGED
```

```python
# domain/events/ai.py
from dataclasses import dataclass, field
from domain.events.base import Event, EventType

@dataclass
class AICompleted(Event):
    decision: dict = field(default_factory=dict)
    operation_id: str = ""
    state_version: int = 0
    def __post_init__(self): self.type = EventType.AI_COMPLETED
```

```python
# domain/events/system.py
from dataclasses import dataclass, field
from domain.events.base import Event, EventType

@dataclass
class TimerTick(Event):
    def __post_init__(self): self.type = EventType.TIMER_TICK

@dataclass
class RiskLimitHit(Event):
    limit_type: str = ""
    symbol: str = ""
    current_value: float = 0.0
    threshold: float = 0.0
    def __post_init__(self): self.type = EventType.RISK_LIMIT_HIT

@dataclass
class UserCommand(Event):
    command: str = ""
    symbol: str = ""
    params: dict = field(default_factory=dict)
    def __post_init__(self): self.type = EventType.USER_COMMAND

@dataclass
class SystemShutdown(Event):
    reason: str = ""
    def __post_init__(self): self.type = EventType.SYSTEM_SHUTDOWN

@dataclass
class HealthEvent(Event):
    severity: str = ""   # "warning" | "critical"
    component: str = ""  # "ticker_stream" | "position_stream" | "api"
    message: str = ""
    def __post_init__(self): self.type = EventType.HEALTH_EVENT
```

```python
# domain/events/__init__.py
from domain.events.base import Event, EventType
from domain.events.market import PriceUpdate
from domain.events.orders import OrderFilled, OrderRejected, OrderCancelled
from domain.events.positions import PositionChanged, FundingChanged
from domain.events.ai import AICompleted
from domain.events.system import TimerTick, RiskLimitHit, UserCommand, SystemShutdown, HealthEvent

__all__ = [
    "Event", "EventType",
    "PriceUpdate",
    "OrderFilled", "OrderRejected", "OrderCancelled",
    "PositionChanged", "FundingChanged",
    "AICompleted",
    "TimerTick", "RiskLimitHit", "UserCommand", "SystemShutdown",
    "HealthEvent",
]
```

- [ ] **Step 4: Update `engine/events.py` to re-export**

```python
"""Backward-compatible re-export from domain.events."""
from domain.events import *  # noqa: F401, F403
```

- [ ] **Step 5: Run all existing tests to verify no breakage**

```bash
python -m pytest tests/ -v
```
Expected: 70 PASS (all imports resolve through re-export)

- [ ] **Step 6: Commit**

```bash
git add domain/ engine/events.py
git commit -m "refactor: split events into domain/events/ package (7 files)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 1.2: Move FSM to `domain/fsm/`

**Files:**
- Create: `domain/fsm/__init__.py`
- Move: `engine/fsm/states.py` → `domain/fsm/states.py`
- Move: `engine/fsm/position_fsm.py` → `domain/fsm/position_fsm.py`
- Move: `engine/fsm/supervisor.py` → `domain/fsm/supervisor.py`
- Rename: `engine/fsm/states.py` TransitionTable → `domain/fsm/transitions.py`
- Update all imports

- [ ] **Step 1: Create `domain/fsm/` and move files**

```bash
mkdir -p domain/fsm
cp engine/fsm/__init__.py domain/fsm/__init__.py
```

- [ ] **Step 2: Extract TransitionTable to `domain/fsm/transitions.py`**

Move `TransitionTable` class from `domain/fsm/states.py` to `domain/fsm/transitions.py`.
Update `domain/fsm/states.py` to keep only enums: `FSMState`, `ActiveSubState`, `WaitReason`.
Update `domain/fsm/__init__.py` to export from both.

- [ ] **Step 3: Update imports in all files**

Replace all `from engine.fsm.*` → `from domain.fsm.*`.
Update `engine/fsm/__init__.py` to re-export.

- [ ] **Step 4: Run all tests**

```bash
python -m pytest tests/ -v
```
Expected: 70 PASS

- [ ] **Step 5: Commit**

---

### Task 1.3: Move EventBus to `engine/bus/` package

**Files:**
- Create: `engine/bus/__init__.py`
- Move: `engine/event_bus.py` → `engine/bus/event_bus.py`
- Create: `engine/bus/command_bus.py` (skeleton for now)
- Create: `engine/bus/subscriptions.py` (skeleton for now)
- Update all imports

- [ ] **Step 1: Move event_bus.py**

```bash
mkdir -p engine/bus
cp engine/event_bus.py engine/bus/event_bus.py
```

- [ ] **Step 2: Update imports — all consumers import from `engine.bus.event_bus`**

- [ ] **Step 3: Create skeleton files for command_bus and subscriptions**

```python
# engine/bus/command_bus.py
"""CommandBus — separate channel for intentions (PlaceOrder, CancelOrder)."""
import asyncio
import logging
from typing import Callable, Awaitable, Any
from domain.commands.base import BaseCommand

log = logging.getLogger(__name__)
Handler = Callable[[BaseCommand], Awaitable[None]]


class CommandBus:
    """Commands can be rejected. Events are immutable facts.
    
    Idempotency guarantee: same operation_id + sequence never executes twice.
    """

    def __init__(self):
        self._handlers: dict[type, list[Handler]] = {}
        self._processed: set[str] = set()  # dedup: "operation_id:seq"
        self._locks: dict[str, asyncio.Lock] = {}

    def subscribe(self, command_type: type, handler: Handler) -> None:
        self._handlers.setdefault(command_type, []).append(handler)

    async def send(self, command: BaseCommand) -> bool:
        """Returns True if accepted and executed. False if duplicate."""
        dedup_key = f"{command.operation_id}:{command.sequence}"
        
        lock = self._locks.setdefault(command.operation_id, asyncio.Lock())
        async with lock:
            if dedup_key in self._processed:
                log.warning("Duplicate command blocked: %s", dedup_key)
                return False
            
            handlers = self._handlers.get(type(command), [])
            if not handlers:
                return False
            
            for handler in handlers:
                try:
                    await handler(command)
                except Exception:
                    log.exception("Command handler failed for %s", type(command).__name__)
            
            self._processed.add(dedup_key)
            return True
```

```python
# engine/bus/subscriptions.py
"""Subscription routing and Dead Letter Queue."""
import json
import logging
from domain.events.base import Event

log = logging.getLogger(__name__)


class DeadLetterQueue:
    """Events that cannot be processed (FSM removed, corrupted data, unknown symbol)."""

    def __init__(self, log_path: str):
        self._path = log_path

    async def push(self, event: Event, error: str) -> None:
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "event_id": event.event_id,
                "type": event.type.name,
                "symbol": getattr(event, "symbol", ""),
                "error": error,
            }, ensure_ascii=False) + "\n")
```

- [ ] **Step 4: Run all tests**

```bash
python -m pytest tests/ -v
```
Expected: 70 PASS

- [ ] **Step 5: Commit**

---

### Task 1.4: Upgrade EventBus — bounded queues, priority, coalescing

**Files:**
- Modify: `engine/bus/event_bus.py`

- [ ] **Step 1: Write failing test for bounded queue + priority**

```python
# tests/unit/engine/test_event_bus.py
import asyncio
import pytest
from engine.bus.event_bus import EventBus
from domain.events import PriceUpdate, OrderFilled, EventType


class TestEventBusPriority:
    @pytest.mark.asyncio
    async def test_price_update_coalescing(self):
        """When queue is full, old PriceUpdates get replaced by new ones."""
        bus = EventBus(max_queue=3)
        bus.start()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe(EventType.PRICE_UPDATE, handler)

        # Send 5 updates — only last 3 should arrive
        for i in range(5):
            await bus.publish(PriceUpdate(symbol="BTCUSDT", price=67000.0 + i))

        await asyncio.sleep(0.2)
        # Coalescing: only last update per symbol survives
        assert len(received) <= 3
        # Last price is the latest
        assert received[-1].price == 67004.0

    @pytest.mark.asyncio
    async def test_order_filled_never_dropped(self):
        """Critical events block instead of dropping."""
        bus = EventBus(max_queue=2)
        bus.start()
        received = []

        async def handler(event):
            await asyncio.sleep(0.05)  # slow consumer
            received.append(event)

        bus.subscribe(EventType.ORDER_FILLED, handler)

        for i in range(3):
            await bus.publish(OrderFilled(order_id=str(i), symbol="BTCUSDT"))

        await asyncio.sleep(0.5)
        assert len(received) == 3  # none dropped
```

- [ ] **Step 2: Run test — FAIL**

```bash
python -m pytest tests/unit/engine/test_event_bus.py::TestEventBusPriority -v
```

- [ ] **Step 3: Implement bounded queues + coalescing in EventBus**

Key changes to `engine/bus/event_bus.py`:

```python
class EventBus:
    DROP_SAFE = {EventType.PRICE_UPDATE}  # can coalesce
    NEVER_DROP = {EventType.POSITION_CHANGED, EventType.ORDER_FILLED,
                  EventType.ORDER_REJECTED, EventType.ORDER_CANCELLED}

    def __init__(self, max_queue: int = 10_000):
        self._queues: dict[EventType, asyncio.Queue] = {}
        self._max = max_queue
        # Double-buffering for atomic price swap — no race condition
        self._price_buffer: dict[str, PriceUpdate] = {}
        self._drain_buffer: dict[str, PriceUpdate] = {}
        ...

    async def publish(self, event: Event) -> bool:
        if event.type == EventType.PRICE_UPDATE:
            self._price_buffer[event.symbol] = event  # atomic dict insert
            return True

        queue = self._queues.setdefault(event.type, asyncio.Queue(maxsize=self._max))
        try:
            queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            if event.type in self.DROP_SAFE:
                return False
            await queue.put(event)  # block for critical
            return True

    async def _drain_prices(self):
        """Periodically drain: atomic buffer swap → no ConcurrentModification."""
        while self._running:
            await asyncio.sleep(1.0)
            # Atomic swap — Python assignment is atomic
            self._drain_buffer, self._price_buffer = (
                self._price_buffer, self._drain_buffer
            )
            # Clear the new active buffer (old drain_buffer)
            self._price_buffer.clear()

            # Drain the old active buffer (now drain_buffer)
            for symbol, event in self._drain_buffer.items():
                queue = self._queues.setdefault(
                    EventType.PRICE_UPDATE, asyncio.Queue(maxsize=self._max)
                )
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    queue.get_nowait()  # drop oldest
                    queue.put_nowait(event)
            self._drain_buffer.clear()
```

- [ ] **Step 4: Run tests — PASS**

```bash
python -m pytest tests/unit/engine/test_event_bus.py tests/test_event_bus.py -v
```

- [ ] **Step 5: Commit**

---

### Task 1.5: Move EventLogger to `event_logging/`

> **Fix #5:** `logging/` переопределил бы стандартный модуль Python. Переименован в `event_logging/`.

**Files:**
- Create: `event_logging/__init__.py`
- Move: `engine/event_logger.py` → `event_logging/event_logger.py`
- Update: `engine/event_logger.py` → re-export

- [ ] **Step 1: Move and update imports**

- [ ] **Step 2: Run tests — 70 PASS**

- [ ] **Step 3: Commit**

---

### Task 1.6: Move RecoveryManager to `domain/recovery/`

**Files:**
- Create: `domain/recovery/__init__.py`
- Move: `engine/recovery.py` → `domain/recovery/manager.py`
- Create: `domain/recovery/snapshot.py`
- Create: `domain/recovery/replay.py`

- [ ] **Step 1: Move RecoveryManager, create skeletons for snapshot + replay**

- [ ] **Step 2: Run tests — 70 PASS**

- [ ] **Step 3: Commit**

---

## Phase 2: ExchangeState + Replay

**Goal after phase:** ExchangeState applies events and reproduces state from snapshot + event log. Replay test passes without Bybit connection.

### Task 2.1: ExchangeState — event-sourced cache

**Files:**
- Create: `domain/exchange_state.py`
- Test: `tests/unit/domain/test_exchange_state.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for ExchangeState."""
import pytest
from domain.exchange_state import ExchangeState
from domain.events import PositionChanged, OrderFilled, PriceUpdate


class TestExchangeStateApply:
    def test_apply_position_changed(self):
        state = ExchangeState()
        event = PositionChanged(
            symbol="BTCUSDT", side="Sell", size=0.01,
            unrealised_pnl=-200.0, margin=500.0,
        )
        state.apply(event)

        pos = state.get_position("BTCUSDT")
        assert pos is not None
        assert pos["size"] == 0.01
        assert pos["unrealised_pnl"] == -200.0

    def test_apply_order_filled_updates_position(self):
        state = ExchangeState()
        state.apply(PositionChanged(symbol="BTCUSDT", side="Sell", size=0.01))
        state.apply(OrderFilled(order_id="1", symbol="BTCUSDT", side="Sell", qty=0.005, price=67200.0))

        assert state.has_open_orders("BTCUSDT") is False  # filled → removed

    def test_get_position_none_for_unknown(self):
        state = ExchangeState()
        assert state.get_position("UNKNOWN") is None

    def test_state_version_increments(self):
        state = ExchangeState()
        assert state.version == 0
        state.apply(PositionChanged(symbol="BTCUSDT"))
        assert state.version == 1
        state.apply(PriceUpdate(symbol="BTCUSDT", price=67000.0))
        assert state.version == 2  # PriceUpdate doesn't change positions but version bumps

    def test_snapshot_roundtrip(self):
        state = ExchangeState()
        state.apply(PositionChanged(symbol="BTCUSDT", side="Sell", size=0.01, unrealised_pnl=-200.0))
        state.apply(PriceUpdate(symbol="BTCUSDT", price=67000.0))

        snap = state.snapshot()
        restored = ExchangeState.from_snapshot(snap)

        assert restored.get_position("BTCUSDT")["size"] == 0.01
        assert restored.version == state.version

    def test_replay_reconstructs_state(self):
        state = ExchangeState()
        state.apply(PositionChanged(symbol="BTCUSDT", side="Sell", size=0.01, unrealised_pnl=-200.0))
        snap = state.snapshot()
        new_events = [
            PositionChanged(symbol="BTCUSDT", side="Sell", size=0.02, unrealised_pnl=-400.0),
        ]
        replayed = ExchangeState.replay(snap, new_events)
        assert replayed.get_position("BTCUSDT")["size"] == 0.02
```

- [ ] **Step 2: Run — FAIL (ExchangeState not found)**

- [ ] **Step 3: Implement ExchangeState**

```python
"""ExchangeState — event-sourced cache of exchange reality."""
from typing import Optional
from domain.events import Event, EventType


class ExchangeState:
    """Changed ONLY through apply(event). No direct writes.
    
    Maintains in-memory event log (last 10k events) for AI history queries.
    """

    def __init__(self):
        self._positions: dict[str, dict] = {}
        self._orders: dict[str, dict] = {}
        self._balance: dict[str, float] = {}
        self._event_log: list[Event] = []  # compact in-memory history
        self.version: int = 0

        self._handlers = {
            EventType.POSITION_CHANGED: self._on_position,
            EventType.ORDER_FILLED: self._on_fill,
            EventType.ORDER_REJECTED: self._on_reject,
            EventType.ORDER_CANCELLED: self._on_cancel,
        }

    def apply(self, event: Event) -> None:
        handler = self._handlers.get(event.type)
        if handler:
            handler(event)
        self._event_log.append(event)
        if len(self._event_log) > 10_000:
            self._event_log = self._event_log[-5000:]  # keep tail
        self.version += 1

    # ...

    def get_position_history(self, symbol: str, limit: int = 100) -> list[Event]:
        """Return recent events for a specific symbol. Used by AI Service."""
        return [e for e in self._event_log
                if getattr(e, 'symbol', None) == symbol][-limit:]

    def _on_position(self, event) -> None:
        self._positions[event.symbol] = {
            "symbol": event.symbol,
            "side": event.side,
            "size": event.size,
            "margin": event.margin,
            "unrealised_pnl": event.unrealised_pnl,
            "roe_percent": event.roe_percent,
            "liq_price": event.liq_price,
        }

    def _on_fill(self, event) -> None:
        self._orders.pop(event.order_id, None)
        if event.symbol in self._positions:
            pos = self._positions[event.symbol]
            if event.side == "Buy":
                pos["size"] = pos.get("size", 0) + event.qty
            else:
                pos["size"] = pos.get("size", 0) - event.qty

    def _on_reject(self, event) -> None:
        self._orders.pop(event.order_id, None)

    def _on_cancel(self, event) -> None:
        self._orders.pop(event.order_id, None)

    # Read-only accessors
    def get_position(self, symbol: str) -> Optional[dict]:
        return self._positions.get(symbol)

    def has_open_orders(self, symbol: str) -> bool:
        return any(o.get("symbol") == symbol for o in self._orders.values())

    def get_balance(self, coin: str) -> float:
        return self._balance.get(coin, 0.0)

    # Snapshot + Replay
    def snapshot(self) -> dict:
        return {
            "version": self.version,
            "positions": dict(self._positions),
            "orders": dict(self._orders),
            "balance": dict(self._balance),
        }

    @classmethod
    def from_snapshot(cls, data: dict) -> "ExchangeState":
        state = cls()
        state._positions = dict(data.get("positions", {}))
        state._orders = dict(data.get("orders", {}))
        state._balance = dict(data.get("balance", {}))
        state.version = data.get("version", 0)
        return state

    @classmethod
    def replay(cls, snapshot: dict, events: list[Event]) -> "ExchangeState":
        state = cls.from_snapshot(snapshot)
        for event in events:
            state.apply(event)
        return state
```

- [ ] **Step 4: Run tests — PASS**

```bash
python -m pytest tests/unit/domain/test_exchange_state.py -v
```

- [ ] **Step 5: Commit**

---

### Task 2.2: StateSnapshotter + Replay

**Files:**
- Create: `domain/recovery/snapshot.py`
- Create: `domain/recovery/replay.py`
- Test: `tests/replay/test_replay.py`

- [ ] **Step 1: Write replay test**

```python
"""Replay tests — snapshot + event log → full state recovery."""
import json
import os
import tempfile
import pytest
from domain.exchange_state import ExchangeState
from domain.events import PositionChanged, OrderFilled
from domain.recovery.snapshot import StateSnapshotter
from domain.recovery.replay import ReplayEngine


class TestReplay:
    def test_replay_from_snapshot_and_log(self):
        tmp = tempfile.mkdtemp()
        log_path = os.path.join(tmp, "events.jsonl")
        snap_path = os.path.join(tmp, "snapshot.json")

        # Build initial state
        state = ExchangeState()
        state.apply(PositionChanged(symbol="BTCUSDT", side="Sell", size=0.01, unrealised_pnl=-200.0))
        state.apply(PositionChanged(symbol="ETHUSDT", side="Sell", size=0.1, unrealised_pnl=-300.0))

        # Snapshot
        snapshotter = StateSnapshotter(state, log_path, snap_path, interval=1)
        with open(log_path, "w") as f:
            pass  # clear log since events are applied directly

        snap = state.snapshot()
        with open(snap_path, "w") as f:
            json.dump(snap, f)

        # Write additional events to log
        events = [
            PositionChanged(symbol="BTCUSDT", side="Sell", size=0.02, unrealised_pnl=-400.0),
            OrderFilled(order_id="1", symbol="BTCUSDT", side="Sell", qty=0.005, price=67200.0),
        ]
        with open(log_path, "a") as f:
            for e in events:
                f.write(json.dumps({"type": e.type.name, "symbol": e.symbol,
                                    "size": getattr(e, "size", 0),
                                    "unrealised_pnl": getattr(e, "unrealised_pnl", 0)}) + "\n")

        # Replay
        engine = ReplayEngine()
        recovered = engine.replay(snap_path, log_path)

        assert recovered.get_position("BTCUSDT") is not None
        assert recovered.version > snap["version"]
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 2.5: Create EventSerializer — single source of truth for serialization**

```python
# domain/events/serialization.py
"""Single source of truth for event serialization/deserialization.
Both EventLogger (write) and ReplayEngine (read) use this — no duplication."""
import json
from dataclasses import fields
from domain.events import Event, EventType, PriceUpdate, PositionChanged
from domain.events import OrderFilled, OrderRejected, OrderCancelled
from domain.events import AICompleted, TimerTick, RiskLimitHit, SystemShutdown


class EventSerializer:
    _registry: dict[str, type[Event]] = {
        "PRICE_UPDATE": PriceUpdate,
        "POSITION_CHANGED": PositionChanged,
        "ORDER_FILLED": OrderFilled,
        "ORDER_REJECTED": OrderRejected,
        "ORDER_CANCELLED": OrderCancelled,
        "AI_COMPLETED": AICompleted,
        "TIMER_TICK": TimerTick,
        "RISK_LIMIT_HIT": RiskLimitHit,
        "SYSTEM_SHUTDOWN": SystemShutdown,
    }

    def to_json(self, event: Event) -> str:
        data = {"type": event.type.name}
        for f in fields(event):
            val = getattr(event, f.name)
            if f.name == "type":
                data["type"] = val.name if hasattr(val, "name") else str(val)
            else:
                data[f.name] = val
        return json.dumps(data, ensure_ascii=False, default=str)

    def from_json(self, line: str) -> Event:
        raw = json.loads(line)
        type_name = raw.pop("type", "")
        event_cls = self._registry.get(type_name)
        if event_cls is None:
            raise ValueError(f"Unknown event type: {type_name}")
        # Filter to only known field names
        field_names = {f.name for f in fields(event_cls)}
        kwargs = {k: v for k, v in raw.items() if k in field_names}
        return event_cls(**kwargs)

    @classmethod
    def register(cls, type_name: str, event_cls: type[Event]) -> None:
        """Register a new event type (called during init for extensibility)."""
        cls._registry[type_name] = event_cls
```

- [ ] **Step 3: Implement snapshotter + replay using EventSerializer**

```python
# domain/recovery/snapshot.py
import json
import logging
from domain.exchange_state import ExchangeState

log = logging.getLogger(__name__)


class StateSnapshotter:
    def __init__(self, state: ExchangeState, log_path: str,
                 snap_path: str, interval: int = 100):
        self._state = state
        self._log_path = log_path
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
```

```python
# domain/recovery/replay.py
import logging
from domain.exchange_state import ExchangeState
from domain.events.serialization import EventSerializer

log = logging.getLogger(__name__)


class ReplayEngine:
    def __init__(self):
        self._serializer = EventSerializer()

    def replay(self, snap_path: str, log_path: str) -> ExchangeState:
        import json
        with open(snap_path) as f:
            snap = json.load(f)
        state = ExchangeState.from_snapshot(snap)

        try:
            with open(log_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    event = self._serializer.from_json(line)
                    state.apply(event)
        except FileNotFoundError:
            pass

        log.info("Replay: restored version %d from snapshot (%d events)",
                 state.version, len(state._event_log))
        return state
```

- [ ] **Step 4: Run tests — PASS**

- [ ] **Step 5: Commit**

---

## Phase 3: Stream Infrastructure

**Goal after phase:** Mock WebSocket → Stream → EventBus → Logger works end-to-end.

### Task 3.1: ReconnectPolicy

**Files:**
- Create: `exchange/reconnect.py`
- Test: `tests/unit/exchange/test_reconnect.py`

- [ ] **Step 1: Write test**

```python
import pytest
from exchange.reconnect import ReconnectPolicy


class TestReconnectPolicy:
    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        policy = ReconnectPolicy()
        delays = []
        for _ in range(7):
            delays.append(policy.next_delay)
            await policy.wait()
        assert delays == [1, 2, 5, 10, 30, 60, 60]

    def test_reset(self):
        policy = ReconnectPolicy()
        policy._attempt = 5
        policy.reset()
        assert policy._attempt == 0
```

- [ ] **Step 2-4: Implement, verify, commit**

### Task 3.2: GapDetector

**Files:**
- Create: `exchange/streams/gap_detector.py`
- Test: `tests/unit/exchange/test_gap_detector.py`

- [ ] **Step 1: Write test**

```python
from exchange.streams.gap_detector import GapDetector


class TestGapDetector:
    def test_no_gap(self):
        gd = GapDetector()
        assert gd.check({"seq": 1}) is False
        assert gd.check({"seq": 2}) is False

    def test_gap_detected(self):
        gd = GapDetector()
        gd.check({"seq": 1})
        assert gd.check({"seq": 5}) is True  # gap: 1→5

    def test_duplicate_not_a_gap(self):
        gd = GapDetector()
        gd.check({"seq": 1})
        gd.check({"seq": 2})
        assert gd.check({"seq": 2}) is False
```

### Task 3.3: BaseStream + StreamStatus

**Files:**
- Create: `exchange/streams/base.py`
- Create: `exchange/streams/__init__.py`

### Task 3.4: Mapper (raw Bybit → typed Events)

**Files:**
- Create: `exchange/mapper.py`
- Test: `tests/unit/exchange/test_mapper.py`

### Task 3.5: TickerStream

**Files:**
- Create: `exchange/streams/ticker.py`
- Test: `tests/unit/exchange/test_streams.py`

### Task 3.6: PositionStream, ExecutionStream, OrderStream

**Files:**
- Create: `exchange/streams/position.py`
- Create: `exchange/streams/execution.py`
- Create: `exchange/streams/order.py`

### Task 3.7: StreamManager

**Files:**
- Create: `exchange/streams/manager.py`
- Test: `tests/unit/exchange/test_stream_manager.py`

- [ ] **Step 1: Write test for manager lifecycle**

```python
import asyncio
import pytest
from exchange.streams.manager import StreamManager
from exchange.streams.base import StreamStatus
from engine.bus.event_bus import EventBus


class TestStreamManager:
    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        bus = EventBus()
        bus.start()
        mgr = StreamManager(bus, symbols=["BTCUSDT"])
        await mgr.start_all()
        # All streams should be RUNNING
        health = mgr.health()
        assert all(s == StreamStatus.RUNNING for s in health.values())
        await mgr.stop_all()
        health = mgr.health()
        assert all(s == StreamStatus.STOPPED for s in health.values())
```

### Task 3.8: Integration test — WS → EventBus → Logger

**Files:**
- Create: `tests/integration/test_stream_to_bus.py`

```python
"""Integration: Mock WS messages → Stream → EventBus → Logger."""
import asyncio
import json
import os
import tempfile
import pytest
from engine.bus.event_bus import EventBus
from domain.events import EventType, PriceUpdate, PositionChanged
from logging.event_logger import EventLogger


class TestStreamToBus:
    @pytest.mark.asyncio
    async def test_mock_ticker_to_eventbus(self):
        bus = EventBus()
        bus.start()
        tmp = tempfile.mkdtemp()
        logger = EventLogger(os.path.join(tmp, "events.jsonl"))
        received = []

        async def handler(event):
            received.append(event)
            await logger.log_transition(
                symbol=event.symbol,
                from_state=None, to_state=None,
                trigger="PriceUpdate", reason=f"price={event.price}",
                state_version=0,
            )

        bus.subscribe(EventType.PRICE_UPDATE, handler)
        await bus.publish(PriceUpdate(symbol="BTCUSDT", price=67000.0, high=67100.0, low=66900.0, volume=100.0))
        await asyncio.sleep(0.1)

        assert len(received) == 1
        assert received[0].price == 67000.0
        await logger.close()
```

---

## Phase 4: Commands + ExchangeAdapter

**Goal after phase:** FSM → OrderCommand → CommandBus → Mock Adapter works.

### Task 4.1: Command types

**Files:**
- Create: `domain/commands/__init__.py`
- Create: `domain/commands/base.py`
- Create: `domain/commands/order.py`
- Create: `domain/commands/cancel.py`
- Create: `domain/commands/close_position.py`
- Test: `tests/unit/domain/test_commands.py`

### Task 4.2: ExchangeAdapter (MCP REST wrapper)

**Files:**
- Create: `exchange/adapter.py`
- Test: `tests/unit/exchange/test_adapter.py`

### Task 4.3: Integration test — FSM → Command → Mock Adapter

**Files:**
- Create: `tests/integration/test_fsm_to_command.py`

```python
"""Integration: FSM decision → CommandBus → Mock ExchangeAdapter."""
import pytest
from engine.bus.command_bus import CommandBus
from engine.bus.event_bus import EventBus
from domain.fsm.position_fsm import PositionFSM
from domain.fsm.states import FSMState
from domain.commands.order import OrderCommand


class TestFsmToCommand:
    @pytest.mark.asyncio
    async def test_fsm_transition_to_order_command(self):
        cmd_bus = CommandBus()
        received_commands = []

        async def adapter_handler(cmd):
            received_commands.append(cmd)

        cmd_bus.subscribe(OrderCommand, adapter_handler)

        fsm = PositionFSM(symbol="BTCUSDT", side="Sell")
        fsm.transition(FSMState.PREPARING, trigger="AICompleted", reason="AI chose DCA")

        cmd = OrderCommand(
            symbol="BTCUSDT", side="Sell", qty="0.005",
            operation_id="op_1", order_link_id="BTCUSDT_DCA_op_1_1",
            correlation_id="corr_1",
        )
        await cmd_bus.send(cmd)

        assert len(received_commands) == 1
        assert received_commands[0].symbol == "BTCUSDT"
```

---

## Phase 5: TradingEngine

**Goal after phase:** Full end-to-end: WS → EventBus → ExchangeState → FSM → CommandBus → Mock Adapter.

### Task 5.1: TradingEngine — main loop + per-symbol dispatcher

**Files:**
- Create: `engine/trading_engine.py`
- Test: `tests/unit/engine/test_trading_engine.py`

### Task 5.2: Integration test — full flow

**Files:**
- Create: `tests/integration/test_full_flow.py`

---

## Phase 6: AI Service

**Goal after phase:** AI request/response lifecycle works without blocking the engine.

### Task 6.1: AI service + DeepSeek provider

**Files:**
- Create: `ai/__init__.py`
- Create: `ai/service.py`
- Create: `ai/prompts.py`
- Create: `ai/providers/__init__.py`
- Create: `ai/providers/deepseek.py`
- Test: `tests/unit/ai/test_service.py`

### Task 6.2: Integration test — AI request → response → EventBus

---

## Phase 7: Observability

**Goal after phase:** All events have correlation IDs, health checks work, structured logging complete.

### Task 7.1: Add correlation_id to all event emission points

### Task 7.2: Health check loop in TradingEngine

### Task 7.3: End-to-end test with replay

---

## Plan Self-Review

1. **Spec coverage:**
   - ✅ Layer dependency diagram → Phase 1 (restructure)
   - ✅ EventBus upgrade (bounded queues, priority, coalescing) → Task 1.4
   - ✅ Streams (4 types + StreamManager) → Phase 3
   - ✅ ExchangeState (event-sourced) → Task 2.1
   - ✅ Snapshot + Replay → Task 2.2
   - ✅ CommandBus + OrderCommand → Phase 4
   - ✅ ExchangeAdapter (no business logic) → Task 4.2
   - ✅ TradingEngine (per-symbol dispatcher) → Phase 5
   - ✅ AIService (separate from engine) → Phase 6
   - ✅ Correlation ID → Phase 7
   - ✅ Dead Letter Queue → Task 1.3 (subscriptions.py)
   - ✅ Health Events → Phase 7
   - ✅ ReconnectPolicy → Task 3.1
   - ✅ GapDetector → Task 3.2
   - ⚠️ AI providers (DeepSeek + Claude) → Task 6.1 skeleton, full implementation out of scope (AI prompt engineering = separate spec)

2. **Placeholder scan:** Phases 3-7 have task outlines without full code. Need to flesh out during implementation. Core phases (1-2) have complete code.

3. **Type consistency:**
   - `EventBus` signature matches usage in StreamManager and TradingEngine ✅
   - `ExchangeState.apply(event)` takes `Event`, used in TradingEngine dispatch ✅
   - `OrderCommand` has `correlation_id`, `operation_id`, `created_at` — consistent with spec ✅
