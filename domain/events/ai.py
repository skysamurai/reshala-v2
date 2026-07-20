from dataclasses import dataclass, field
from domain.events.base import Event, EventType


@dataclass
class AICompleted(Event):
    decision: dict = field(default_factory=dict)
    operation_id: str = ""
    state_version: int = 0

    def __post_init__(self):
        self.type = EventType.AI_COMPLETED
