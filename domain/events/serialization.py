"""Single source of truth for event serialization/deserialization.
Both EventLogger (write) and ReplayEngine (read) use this — no duplication."""
import json
from dataclasses import fields
from domain.events import Event, PriceUpdate, PositionChanged
from domain.events import OrderFilled, OrderRejected, OrderCancelled
from domain.events import AICompleted, TimerTick, RiskLimitHit, SystemShutdown, HealthEvent


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
        "HEALTH_EVENT": HealthEvent,
    }

    def to_json(self, event: Event) -> str:
        data = {"type": event.type.name}
        for f in fields(event):
            val = getattr(event, f.name)
            if f.name == "type":
                continue  # handled above
            data[f.name] = val
        return json.dumps(data, ensure_ascii=False, default=str)

    def from_json(self, line: str) -> Event:
        raw = json.loads(line)
        type_name = raw.pop("type", "")
        event_cls = self._registry.get(type_name)
        if event_cls is None:
            raise ValueError(f"Unknown event type: {type_name}")
        field_names = {f.name for f in fields(event_cls)}
        kwargs = {k: v for k, v in raw.items() if k in field_names}
        return event_cls(**kwargs)
