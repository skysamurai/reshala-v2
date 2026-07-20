# ADR 005: Layer Dependencies — Domain Never Knows Infrastructure

**Date:** 2026-07-20
**Status:** Accepted

## Context

Trading bots easily become spaghetti: AI code calls exchange API directly, FSM reads WebSocket messages, risk checks are scattered across files. This makes testing impossible without a live Bybit connection.

## Decision

**Three strict layers with unidirectional dependencies:**

```
Application  (engine/trading_engine.py, ai/)
     ↓
Domain       (domain/exchange_state.py, domain/fsm/, domain/events/, domain/commands/)
     ↓
Infrastructure (exchange/, engine/bus/, logging/)
```

**Rule:** Domain NEVER imports from Infrastructure.

- ✅ `from domain.commands import OrderCommand` (domain import in domain)
- ✅ `from exchange.adapter import ExchangeAdapter` (infrastructure import in application)
- ❌ `from exchange.adapter import ExchangeAdapter` (infrastructure import in domain — FORBIDDEN)

## Enforcement

Can be checked at CI with `pytest --import-mode=importlib` + a lint rule:

```bash
# Fails if domain/ imports exchange/
grep -r "from exchange\." domain/ && exit 1
grep -r "import exchange" domain/ && exit 1
```

## Alternatives Considered

- **Hexagonal architecture (ports & adapters)** — same idea, more ceremony. This is a pragmatic subset.
- **No layers, just modules** — works for small projects, breaks at scale.
- **Dependency inversion via interfaces** — adds ABC overhead without clear benefit for this scale.

## Consequences

- ✅ Domain is fully testable without Bybit, MCP, or network
- ✅ Replay tests: feed historical events to domain → verify FSM behavior
- ✅ Swap infrastructure: change Bybit client without touching business logic
- ✅ Clear import rules: grep-able, CI-enforceable
- ⚠️ Requires discipline: "just quickly import adapter here" must be rejected in review
- ⚠️ Application layer must do the wiring (dependency injection at startup)
