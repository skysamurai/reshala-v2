"""RecoveryManager — reconcile FSM state with exchange reality after restart."""
import logging
from typing import Optional
from engine.fsm.position_fsm import PositionFSM
from engine.fsm.states import FSMState

log = logging.getLogger(__name__)


class RecoveryManager:
    """Reconciles internal FSM state with actual exchange state.

    Called on BOOT → RECOVERING. The exchange is the single source of truth.
    Any discrepancy between FSM expectations and exchange reality resolves
    in favor of the exchange.

    Reconciliation steps:
    1. Fetch all positions from exchange
    2. Fetch all open orders from exchange
    3. Fetch recent execution history
    4. For each losing position, create or restore a PositionFSM
    5. Determine correct initial state based on open orders and fills
    """

    def reconcile(
        self,
        positions: list[dict],
        open_orders: list[dict],
        execution_history: list[dict],
    ) -> list[PositionFSM]:
        """Reconcile exchange state into PositionFSM instances.

        Args:
            positions: Raw position data from exchange
            open_orders: Raw open order data from exchange
            execution_history: Recent fills from exchange

        Returns:
            List of PositionFSM instances, one per losing position
        """
        fsms: list[PositionFSM] = []

        # Index orders by symbol
        orders_by_symbol: dict[str, list[dict]] = {}
        for o in open_orders:
            sym = o.get("symbol", "")
            orders_by_symbol.setdefault(sym, []).append(o)

        # Index executions by symbol
        executions_by_symbol: dict[str, list[dict]] = {}
        for e in execution_history:
            sym = e.get("symbol", "")
            executions_by_symbol.setdefault(sym, []).append(e)

        for pos in positions:
            if self._is_losing(pos):
                fsm = self._create_fsm_for_position(
                    pos,
                    orders_by_symbol.get(pos["symbol"], []),
                    executions_by_symbol.get(pos["symbol"], []),
                )
                fsms.append(fsm)

        log.info("Recovery: created %d FSM(s) from exchange state", len(fsms))
        return fsms

    def _is_losing(self, pos: dict) -> bool:
        """Check if a position is losing (needs recovery)."""
        return pos.get("unrealised_pnl", 0) < 0

    def _create_fsm_for_position(
        self,
        pos: dict,
        orders: list[dict],
        executions: list[dict],
    ) -> PositionFSM:
        """Create a PositionFSM with the correct initial state."""
        symbol = pos["symbol"]
        side = pos["side"]

        fsm = PositionFSM(
            symbol=symbol,
            side=side,
            initial_state=FSMState.RECOVERING,
        )

        # Transition to correct state based on exchange reality
        initial_state = self._determine_initial_state(symbol, side, orders, executions)
        fsm.transition(
            initial_state,
            trigger="RecoveryComplete",
            reason=f"reconciled from exchange: {len(orders)} open orders, {len(executions)} recent fills",
        )

        log.info("Recovery: %s %s → %s", symbol, side, fsm.state.value)
        return fsm

    def _determine_initial_state(
        self,
        symbol: str,
        side: str,
        orders: list[dict],
        executions: list[dict],
    ) -> FSMState:
        """Determine the correct initial FSM state from exchange data.

        Logic:
        - Has open limit orders matching side → WAIT_FILL
        - Has open orders with known orderLinkId pattern → VERIFY
        - Has recent fills → ACTIVE (DCA/HEDGE/SCALP executed)
        - No orders, losing position → IDLE
        """
        matching_orders = [
            o for o in orders
            if o.get("symbol") == symbol and o.get("side") == side
        ]

        if matching_orders:
            for o in matching_orders:
                link_id = o.get("orderLinkId", "")
                if self._is_known_order(link_id):
                    return FSMState.WAIT_FILL
            # Orders exist but don't match known patterns → they need verification
            return FSMState.VERIFY

        if executions:
            latest_fill_time = max(
                (e.get("execTime", 0) for e in executions
                 if e.get("symbol") == symbol and e.get("side") == side),
                default=0,
            )
            if latest_fill_time > 0:
                return FSMState.ACTIVE

        return FSMState.IDLE

    def _is_known_order(self, order_link_id: str) -> bool:
        """Check if orderLinkId matches the bot's naming convention."""
        # Pattern: SYMBOL_STRATEGY_OPID_SEQ
        parts = order_link_id.split("_")
        return len(parts) >= 4
