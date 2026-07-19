"""Reshala v2 — Event-driven trading engine with per-position FSM.

Public API:
    EventBus         — Pub/sub event dispatcher
    EventLogger      — JSONL black box for FSM transitions
    PositionFSM      — Per-symbol state machine
    GlobalSupervisor — System health monitor
    RecoveryManager  — Exchange state reconciliation

Event types:
    PriceUpdate, OrderFilled, OrderRejected, OrderCancelled,
    PositionChanged, FundingChanged, AICompleted, TimerTick,
    RiskLimitHit, UserCommand, SystemShutdown
"""

from engine.event_bus import EventBus
from engine.event_logger import EventLogger
from engine.fsm.position_fsm import PositionFSM
from engine.fsm.supervisor import GlobalSupervisor
from engine.recovery import RecoveryManager

__all__ = [
    "EventBus",
    "EventLogger",
    "PositionFSM",
    "GlobalSupervisor",
    "RecoveryManager",
]
