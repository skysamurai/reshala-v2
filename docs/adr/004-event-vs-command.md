# ADR 004: Separate EventBus and CommandBus

**Date:** 2026-07-20
**Status:** Accepted

## Context

The system has two fundamentally different message types:

- **Facts** (happened, can't undo): PriceUpdate, OrderFilled, PositionChanged
- **Intentions** (may be rejected): PlaceOrder, CancelOrder

Mixing both on a single bus creates ambiguity: is this message describing reality or wanting to change it?

## Decision

**Two separate buses:**

```python
EventBus    # facts — Streams publish, ExchangeState + FSM subscribe
CommandBus  # intentions — FSM publishes, ExchangeAdapter subscribes
```

Events flow: `Bybit WS → Streams → EventBus → ExchangeState → FSM`
Commands flow: `FSM → CommandBus → ExchangeAdapter → Bybit REST`

## Alternatives Considered

- **Single bus with type field** — simpler but loses the semantic distinction. Can't enforce "commands can be rejected."
- **Direct method calls** — FSM calls `adapter.place_order()`. Couples domain to infrastructure.
- **Actor model** — overkill for single-process Python app.

## Consequences

- ✅ Clear separation: facts vs intentions visible in architecture
- ✅ Commands can be rejected, events are immutable
- ✅ Easier debugging: trace events for "what happened", commands for "what we tried"
- ✅ Domain doesn't know about Bybit — only emits OrderCommands
- ⚠️ Two buses to configure, two subscriber registries
- ⚠️ Must ensure CommandBus never drops messages (unlike EventBus where PriceUpdate can coalesce)
