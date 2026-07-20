# ADR 001: Event Sourcing for ExchangeState

**Date:** 2026-07-20
**Status:** Accepted

## Context

ExchangeState must reflect the real state of positions and orders on Bybit. Changes can come from WebSocket events, REST reconciliation, or recovery after restart. State must be reproducible for debugging and audit.

## Decision

**ExchangeState is event-sourced.** It changes ONLY through `apply(event)`. No direct field assignments from outside the class.

```python
state.apply(PositionChanged(...))  # ✅ only way to modify
state.positions["BTCUSDT"] = {...}  # ❌ never allowed
```

Every state mutation produces an `Event` logged to JSONL. Snapshot is taken every 100 events for fast recovery.

## Alternatives Considered

- **Mutable state with setters** — simpler but unreproducible. Can't replay.
- **CRDT-based state** — overengineered for single-process system.
- **Full CQRS with separate read/write models** — premature for current scale.

## Consequences

- ✅ Full reproducibility: snapshot + event log = current state
- ✅ Auditable: every change has event_id, timestamp, correlation_id
- ✅ Testable: replay historical events against FSM
- ⚠️ Migration cost: existing state.json must be converted to event log
- ⚠️ Performance: apply() must be fast (<1ms). No blocking I/O inside.
