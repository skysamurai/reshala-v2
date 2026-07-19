"""GlobalSupervisor — system health monitor and risk gate."""
import logging
import time
from enum import Enum, auto
from typing import Optional
from engine.fsm.position_fsm import PositionFSM
from engine.events import RiskLimitHit

log = logging.getLogger(__name__)


class SupervisorState(Enum):
    HEALTHY = auto()
    RISK_LIMITED = auto()       # A risk limit is active
    DEGRADED = auto()           # Minor issues (stuck FSM, slow API)
    CRITICAL = auto()           # Major issue — API down, exchange maintenance


class GlobalSupervisor:
    """Monitors system health across all PositionFSMs.

    Responsibilities:
    - Track all active PositionFSMs
    - Detect stuck FSMs (no events for too long)
    - Track risk limits (daily loss, drawdown, position margin)
    - Report health status
    """

    def __init__(self, stuck_timeout_seconds: int = 600):
        self.state: SupervisorState = SupervisorState.HEALTHY
        self.fsms: dict[str, PositionFSM] = {}
        self.active_limits: dict[str, RiskLimitHit] = {}
        self._last_event_ts: dict[str, float] = {}
        self._stuck_timeout = stuck_timeout_seconds

    # ─── FSM Registry ─────────────────────────────────────

    def _fsm_key(self, symbol: str, side: str) -> str:
        return f"{symbol}_{side}"

    def register_fsm(self, fsm: PositionFSM) -> None:
        key = self._fsm_key(fsm.symbol, fsm.side)
        self.fsms[key] = fsm
        self._last_event_ts[key] = time.time()
        log.info("Supervisor: registered %s (%s)", key, fsm.state.value)

    def unregister_fsm(self, symbol: str, side: str) -> None:
        key = self._fsm_key(symbol, side)
        self.fsms.pop(key, None)
        self._last_event_ts.pop(key, None)
        log.info("Supervisor: unregistered %s", key)

    def touch(self, fsm_key: str) -> None:
        """Record that an FSM received an event (not stuck)."""
        self._last_event_ts[fsm_key] = time.time()

    # ─── Health Check ─────────────────────────────────────

    async def check_health(self) -> list[str]:
        """Run health check and return list of issues (empty = all OK)."""
        issues = []
        now = time.time()

        for key in list(self.fsms.keys()):
            last_ts = self._last_event_ts.get(key, 0)
            if now - last_ts > self._stuck_timeout:
                fsm = self.fsms[key]
                issues.append(
                    f"FSM {key} stuck in {fsm.state.value} "
                    f"for {int(now - last_ts)}s"
                )

        if issues:
            if self.state == SupervisorState.HEALTHY:
                self.state = SupervisorState.DEGRADED
        elif self.state == SupervisorState.DEGRADED and not self.active_limits:
            self.state = SupervisorState.HEALTHY

        return issues

    # ─── Risk Limits ──────────────────────────────────────

    def handle_risk_limit(self, event: RiskLimitHit) -> None:
        """Process a risk limit hit event."""
        self.active_limits[event.limit_type] = event
        self.state = SupervisorState.RISK_LIMITED
        log.warning(
            "Supervisor: RISK LIMIT %s hit for %s (%.2f > %.2f)",
            event.limit_type, event.symbol, event.current_value, event.threshold,
        )

    def clear_risk_limit(self, limit_type: str) -> None:
        """Clear a specific risk limit after user acknowledgment."""
        self.active_limits.pop(limit_type, None)
        if not self.active_limits and self.state == SupervisorState.RISK_LIMITED:
            self.state = SupervisorState.HEALTHY
            log.info("Supervisor: all risk limits cleared → HEALTHY")

    def is_risk_limited(self) -> bool:
        return self.state == SupervisorState.RISK_LIMITED

    # ─── Status ───────────────────────────────────────────

    def summary(self) -> dict:
        return {
            "state": self.state.name,
            "fsm_count": len(self.fsms),
            "active_limits": list(self.active_limits.keys()),
            "fsm_states": {
                key: fsm.summary() for key, fsm in self.fsms.items()
            },
        }
