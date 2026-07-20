"""Risk Engine — three-level guard system.

Level 1: Per-trade limits (position size, max DCA, leverage)
Level 2: Global limits (daily loss, drawdown, max concurrent positions)
Level 3: System/circuit breakers (consecutive errors, API failures)

Pure domain component — no Bybit knowledge.
Publishes RiskLimitHit events when thresholds are breached.
"""
import logging
from dataclasses import dataclass, field
from domain.events import RiskLimitHit

log = logging.getLogger(__name__)


@dataclass
class RiskLimits:
    """Configurable risk limits."""
    # Level 1: Per-trade
    max_position_size_usd: float = 500.0
    max_leverage: int = 10
    max_dca_per_position: int = 5
    max_slippage_pct: float = 2.0

    # Level 2: Global
    daily_loss_cap_usd: float = 500.0
    max_drawdown_pct: float = 50.0
    max_concurrent_positions: int = 5
    max_total_exposure_usd: float = 5000.0

    # Level 3: System
    max_consecutive_errors: int = 5
    max_api_latency_ms: float = 5000.0
    circuit_breaker_cooldown_s: int = 300


class RiskEngine:
    """Validates every trade against risk limits.

    Subscribes to EventBus. Publishes RiskLimitHit when breached.
    Does NOT make trading decisions — only checks and alerts.
    """

    def __init__(self, limits: RiskLimits | None = None):
        self.limits = limits or RiskLimits()
        self._dca_count: dict[str, int] = {}
        self._daily_loss: float = 0.0
        self._consecutive_errors: int = 0
        self._circuit_open: bool = False
        self.on_risk_limit_hit = None  # async callback(event)

    # ─── Level 1: Per-trade ───────────────────────────────

    def check_order_size(self, symbol: str, qty: float, price: float) -> bool:
        """Check if order size is within per-trade USD limit."""
        notional = qty * price
        if notional > self.limits.max_position_size_usd:
            log.warning("RISK L1: %s order size $%.2f > limit $%.2f",
                        symbol, notional, self.limits.max_position_size_usd)
            return False
        return True

    def can_dca(self, fsm_key: str) -> bool:
        """Check if another DCA round is allowed for this position."""
        return self._dca_count.get(fsm_key, 0) < self.limits.max_dca_per_position

    def record_dca(self, fsm_key: str) -> None:
        self._dca_count[fsm_key] = self._dca_count.get(fsm_key, 0) + 1

    def reset_dca(self, fsm_key: str) -> None:
        self._dca_count.pop(fsm_key, None)

    # ─── Level 2: Global ──────────────────────────────────

    def check_daily_loss(self) -> bool:
        """True if within daily loss cap."""
        if self._daily_loss > self.limits.daily_loss_cap_usd:
            log.warning("RISK L2: daily loss $%.2f > cap $%.2f",
                        self._daily_loss, self.limits.daily_loss_cap_usd)
            return False
        return True

    def record_realised_loss(self, symbol: str, amount: float) -> RiskLimitHit | None:
        """Record realised loss. Returns RiskLimitHit if daily cap exceeded."""
        self._daily_loss += abs(amount)
        if not self.check_daily_loss():
            return self.check_and_warn(
                symbol, "daily_loss",
                f"Daily loss ${self._daily_loss:.2f} > cap ${self.limits.daily_loss_cap_usd:.2f}"
            )
        return None

    def can_open_position(self, current_count: int) -> bool:
        return current_count < self.limits.max_concurrent_positions

    # ─── Level 3: Circuit breaker ─────────────────────────

    def record_error(self) -> None:
        self._consecutive_errors += 1
        if self._consecutive_errors >= self.limits.max_consecutive_errors:
            self._circuit_open = True
            log.error("RISK L3: circuit breaker OPEN after %d errors",
                      self._consecutive_errors)

    def is_circuit_open(self) -> bool:
        return self._circuit_open

    def reset_errors(self) -> None:
        self._consecutive_errors = 0
        self._circuit_open = False

    # ─── Events ───────────────────────────────────────────

    def check_and_warn(self, symbol: str, limit_type: str, message: str) -> RiskLimitHit | None:
        """Create a RiskLimitHit event for any breached limit."""
        event = RiskLimitHit(
            limit_type=limit_type,
            symbol=symbol,
            current_value=self._daily_loss if limit_type == "daily_loss" else 0.0,
            threshold=getattr(self.limits, f"max_{limit_type}", 0.0),
        )
        log.warning("RISK: %s — %s", limit_type, message)
        return event
