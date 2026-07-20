"""TradingEngine — main loop with per-symbol dispatcher.

One dispatcher per symbol → parallel execution, no races within a symbol.
FSM reads ExchangeState (not raw events). Commands go to CommandBus.
"""
import asyncio
import logging
from domain.fsm.position_fsm import PositionFSM
from domain.fsm.states import FSMState
from domain.fsm.supervisor import GlobalSupervisor
from domain.exchange_state import ExchangeState
from domain.recovery.manager import RecoveryManager
from domain.events import EventType
from domain.commands.order import OrderCommand
from engine.bus.event_bus import EventBus
from engine.bus.command_bus import CommandBus

log = logging.getLogger(__name__)


class TradingEngine:
    """Main orchestrator. Coordinates streams, FSM, exchange adapter, AI.

    Architecture:
    - Per-symbol event loop: one asyncio task per symbol
    - Within a symbol: strict sequential event processing
    - FSM → ExchangeState (read) → OrderCommand (write)
    """

    def __init__(
        self,
        bus: EventBus,
        cmd_bus: CommandBus,
        adapter,      # ExchangeAdapter
        ai_service,   # AIService
        symbols: list[str],
    ):
        self._bus = bus
        self._cmd_bus = cmd_bus
        self._adapter = adapter
        self._ai = ai_service
        self._symbols = symbols

        self._state = ExchangeState()
        self._supervisor = GlobalSupervisor()
        self._fsms: dict[str, PositionFSM] = {}
        self._running = False

    # ─── Lifecycle ────────────────────────────────────────

    async def run(self) -> None:
        self._running = True

        # 1. Recovery — reconcile with exchange
        await self._recover()

        # 2. Per-symbol event loops
        tasks = [
            asyncio.create_task(self._symbol_loop(symbol, fsm))
            for symbol, fsm in self._fsms.items()
        ]
        if not tasks:
            log.warning("No FSMs to run — engine idle")
        await asyncio.gather(*tasks, return_exceptions=True)

    async def shutdown(self) -> None:
        self._running = False
        log.info("TradingEngine shutdown")

    # ─── Recovery ─────────────────────────────────────────

    async def _recover(self) -> None:
        positions = await self._adapter.fetch_positions()
        orders = await self._adapter.fetch_open_orders()
        mgr = RecoveryManager()
        fsms = mgr.reconcile(positions, orders, [])

        for fsm in fsms:
            key = self._supervisor._fsm_key(fsm.symbol, fsm.side)
            self._fsms[key] = fsm
            self._supervisor.register_fsm(fsm)
            # Initialize ExchangeState from exchange data
            pos = next((p for p in positions if p.get("symbol") == fsm.symbol), None)
            if pos:
                from exchange.mapper import to_position_changed
                self._state.apply(to_position_changed(pos))

        log.info("Recovery: %d FSM(s) reconciled", len(self._fsms))

    # ─── Per-symbol loop ──────────────────────────────────

    async def _symbol_loop(self, symbol: str, fsm: PositionFSM) -> None:
        """Sequential event processing for one symbol. No races."""
        log.info("Symbol loop started: %s %s", symbol, fsm.state.value)
        while self._running:
            await asyncio.sleep(0.5)  # heartbeat / timer tick
            self._supervisor.touch(self._supervisor._fsm_key(symbol, fsm.side))

            # Check if we should request AI decision
            if fsm.state == FSMState.IDLE and self._should_evaluate(fsm):
                await self._request_ai(fsm)

    # ─── AI → FSM → Command chain ─────────────────────────

    async def _request_ai(self, fsm: PositionFSM) -> None:
        """Request AI decision asynchronously. Result comes as AICompleted event."""
        if self._ai:
            await self._ai.request_decision(fsm, self._state)

    def _should_evaluate(self, fsm: PositionFSM) -> bool:
        """Check if FSM is ready for AI evaluation."""
        return fsm.state == FSMState.IDLE and self._state.get_position(fsm.symbol) is not None

    # ─── Event handlers (called from EventBus subscribers) ─

    async def on_ai_completed(self, event) -> None:
        """AICompleted → FSM transition to PREPARING."""
        fsm = self._find_fsm(event)
        if fsm is None:
            log.warning("AICompleted for unknown symbol: %s", event.symbol)
            return
        if not fsm.is_current_version(event.state_version):
            log.info("Stale AI decision for %s (v%d != v%d)",
                     fsm.symbol, event.state_version, fsm.state_version)
            return

        ok = fsm.transition(
            FSMState.PREPARING,
            trigger="AICompleted",
            reason=event.decision.get("reasoning", ""),
            operation_id=event.operation_id,
        )
        if ok:
            log.info("%s: AI → PREPARING — %s", fsm.symbol, event.decision.get("strategy", "?"))

    async def on_order_filled(self, event) -> None:
        """OrderFilled → FSM WAIT_FILL → ACTIVE."""
        fsm = self._find_fsm(event)
        if fsm is None:
            return
        if fsm.state == FSMState.WAIT_FILL:
            fsm.transition(FSMState.ACTIVE, trigger="OrderFilled",
                          reason=f"filled {event.qty} @ {event.price}")

    async def on_order_rejected(self, event) -> None:
        """OrderRejected → FSM WAIT_FILL → VERIFY."""
        fsm = self._find_fsm(event)
        if fsm and fsm.state == FSMState.WAIT_FILL:
            fsm.transition(FSMState.VERIFY, trigger="OrderRejected",
                          reason=event.reason)

    async def on_position_changed(self, event) -> None:
        """PositionChanged → reconcile FSM with exchange reality."""
        # Exchange always wins
        self._state.apply(event)
        fsm = self._find_fsm(event)
        if fsm:
            pos = self._state.get_position(event.symbol)
            if pos and pos.get("size", 0) == 0 and fsm.state != FSMState.IDLE:
                # Position closed externally
                fsm.transition(FSMState.IDLE, trigger="PositionChanged",
                              reason="position closed on exchange")

    def _find_fsm(self, event) -> PositionFSM | None:
        symbol = getattr(event, "symbol", "")
        side = getattr(event, "side", "")
        # Try both side variants
        for s in [side, "Sell", "Buy"]:
            key = self._supervisor._fsm_key(symbol, s)
            if key in self._fsms:
                return self._fsms[key]
        return None
