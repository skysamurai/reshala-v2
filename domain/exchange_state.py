"""ExchangeState — event-sourced cache of exchange reality.

Changed ONLY through apply(event). No direct writes from outside.
Maintains in-memory event log (last 10k) for AI history queries.
"""
from typing import Optional
from domain.events import Event, EventType


class ExchangeState:
    """Event-sourced cache. apply() is the only way to modify state."""

    # Event types that change state (version increments)
    STATE_EVENTS = {
        EventType.POSITION_CHANGED, EventType.ORDER_FILLED,
        EventType.ORDER_REJECTED, EventType.ORDER_CANCELLED,
    }

    def __init__(self):
        self._positions: dict[str, dict] = {}
        self._orders: dict[str, dict] = {}
        self._balance: dict[str, float] = {}
        self._event_log: list[Event] = []
        self.version: int = 0

        self._handlers = {
            EventType.POSITION_CHANGED: self._on_position,
            EventType.ORDER_FILLED: self._on_fill,
            EventType.ORDER_REJECTED: self._on_reject,
            EventType.ORDER_CANCELLED: self._on_cancel,
        }

    def apply(self, event: Event) -> None:
        """Apply event to state. Only way to modify ExchangeState."""
        handler = self._handlers.get(event.type)
        if handler:
            handler(event)
        self._event_log.append(event)
        if len(self._event_log) > 10_000:
            self._event_log = self._event_log[-5000:]
        if event.type in self.STATE_EVENTS:
            self.version += 1

    # ─── Event handlers (private) ─────────────────────────

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

    # ─── Read-only accessors ──────────────────────────────

    def get_position(self, symbol: str) -> Optional[dict]:
        return self._positions.get(symbol)

    def has_open_orders(self, symbol: str) -> bool:
        return any(o.get("symbol") == symbol for o in self._orders.values())

    def get_balance(self, coin: str) -> float:
        return self._balance.get(coin, 0.0)

    def get_position_history(self, symbol: str, limit: int = 100) -> list[Event]:
        """Return recent events for a symbol. Used by AI Service."""
        return [e for e in self._event_log
                if getattr(e, 'symbol', None) == symbol][-limit:]

    # ─── Snapshot ─────────────────────────────────────────

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
        """Reconstruct state from snapshot + events."""
        state = cls.from_snapshot(snapshot)
        for event in events:
            state.apply(event)
        return state
