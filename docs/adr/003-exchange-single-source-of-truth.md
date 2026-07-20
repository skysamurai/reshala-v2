# ADR 003: Exchange = Single Source of Truth

**Date:** 2026-07-20
**Status:** Accepted

## Context

Position state on Bybit can change without bot's action: manual close via UI, partial liquidation, TP/SL trigger, margin change, funding fee deduction. The bot must never operate on stale assumptions.

## Decision

**Exchange is the single source of truth.** When `PositionChanged` event arrives:

1. `ExchangeState.apply(event)` updates local cache
2. `TradingEngine._dispatch()` compares FSM expectations vs exchange reality
3. Any discrepancy resolves in favor of the exchange
4. FSM transitions to reconciled state (or IDLE if position unexpectedly closed)

```
if not position_matches_fsm(fsm, exchange_state):
    reconcile_fsm(fsm, exchange_state)  # exchange wins
```

## Alternatives Considered

- **FSM as source of truth** — dangerous. Bot could think position is open when it's been liquidated.
- **Last-write-wins** — ambiguous. Which write is "last" when WS events are unordered?
- **Optimistic locking with version check** — adds complexity without clear benefit over "exchange wins."

## Consequences

- ✅ Bot never operates on phantom positions
- ✅ Recovery after crash is simple: fetch positions → reconcile
- ✅ Defensive: even if FSM has a bug, exchange reality overrides
- ⚠️ Must reconcile gracefully — sudden IDLE from ACTIVE means position was closed externally
- ⚠️ Requires PositionStream to be the highest-priority stream (never drop events)
