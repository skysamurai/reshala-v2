# ADR 002: Per-Position FSM (not Global FSM)

**Date:** 2026-07-20
**Status:** Accepted

## Context

The trading bot manages multiple losing positions simultaneously (BTC, ETH, SOL, etc.). Each position follows a state machine: IDLE → PREPARING → SENDING_ORDER → VERIFY → WAIT_FILL → ACTIVE → CLOSING → IDLE.

## Decision

**Each position gets its own PositionFSM instance.** Not a single global FSM for the entire application.

```python
fsm_btc = PositionFSM("BTCUSDT", "Sell")
fsm_eth = PositionFSM("ETHUSDT", "Sell")
```

Transitions are validated by a deterministic `TransitionTable`. State + Event = Next State. Nothing else.

## Alternatives Considered

- **Global FSM** — simpler but can't handle multiple concurrent positions. One stuck position blocks all others.
- **State pattern (GoF)** — too much boilerplate per state. 14 states × ~8 transitions each = unmanageable.
- **Rule engine** — dynamic rules are harder to test. Deterministic table wins for trading.

## Consequences

- ✅ Isolated failures: one position in ERROR doesn't affect others
- ✅ Independent cooldowns and limits per symbol
- ✅ Deterministic: TransitionTable has no side effects, fully testable
- ✅ Per-symbol dispatcher enables parallel event processing without races
- ⚠️ 14 states × up to 10 exits = ~140 transitions to maintain in table
