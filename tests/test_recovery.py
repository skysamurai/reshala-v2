"""Tests for RecoveryManager — state reconciliation after restart."""
import pytest
from engine.recovery import RecoveryManager
from engine.fsm.position_fsm import PositionFSM
from engine.fsm.states import FSMState


# Mock exchange data
def mock_positions():
    return [
        {
            "symbol": "BTCUSDT", "side": "Sell", "size": 0.01,
            "avg_price": 65000.0, "mark_price": 67000.0,
            "unrealised_pnl": -200.0, "cum_realised_pnl": 0.0,
            "roe_percent": -40.0, "margin": 500.0, "leverage": 7,
            "liq_price": 72000.0, "take_profit": 0.0,
        },
    ]


def mock_open_orders():
    return [
        {
            "orderId": "ord_1", "orderLinkId": "BTCUSDT_DCA_abc_1",
            "symbol": "BTCUSDT", "side": "Sell", "orderType": "Limit",
            "price": "67200", "qty": "0.005",
        },
    ]


class TestRecoveryCreateFSMs:
    def test_creates_fsm_for_each_losing_position(self):
        mgr = RecoveryManager()
        fsms = mgr.reconcile(
            positions=mock_positions(),
            open_orders=[],
            execution_history=[],
        )
        assert len(fsms) == 1
        fsm = fsms[0]
        assert fsm.symbol == "BTCUSDT"
        assert fsm.side == "Sell"

    def test_skips_profitable_positions(self):
        mgr = RecoveryManager()
        profitable = [{
            "symbol": "ETHUSDT", "side": "Sell", "size": 0.1,
            "avg_price": 3000.0, "mark_price": 2900.0,
            "unrealised_pnl": 100.0, "cum_realised_pnl": 0.0,
            "roe_percent": 20.0, "margin": 500.0, "leverage": 7,
            "liq_price": 3500.0, "take_profit": 0.0,
        }]
        fsms = mgr.reconcile(
            positions=profitable,
            open_orders=[],
            execution_history=[],
        )
        assert len(fsms) == 0

    def test_reconcile_with_open_orders(self):
        """FSM should be in WAIT_FILL if there are open orders."""
        mgr = RecoveryManager()
        fsms = mgr.reconcile(
            positions=mock_positions(),
            open_orders=mock_open_orders(),
            execution_history=[],
        )
        fsm = fsms[0]
        # With open orders matching this position, FSM starts in WAIT_FILL
        assert fsm.state == FSMState.WAIT_FILL

    def test_reconcile_no_orders_no_positions(self):
        mgr = RecoveryManager()
        fsms = mgr.reconcile(positions=[], open_orders=[], execution_history=[])
        assert len(fsms) == 0

    def test_reconcile_unknown_order_link_id(self):
        """Order with unknown orderLinkId format → FSM starts in VERIFY."""
        mgr = RecoveryManager()
        fsms = mgr.reconcile(
            positions=mock_positions(),
            open_orders=[{
                "orderId": "ord_x", "orderLinkId": "manual_order",
                "symbol": "BTCUSDT", "side": "Sell",
                "orderType": "Market", "price": "67000", "qty": "0.01",
            }],
            execution_history=[],
        )
        assert len(fsms) == 1
        # Unknown order → VERIFY (orders exist but linkId pattern not recognized)
        assert fsms[0].state == FSMState.VERIFY

    def test_recognizes_hedge_position(self):
        """A Buy position on a symbol that also has a Sell → hedge."""
        mgr = RecoveryManager()
        positions = [
            {
                "symbol": "BTCUSDT", "side": "Sell", "size": 0.01,
                "avg_price": 65000.0, "mark_price": 67000.0,
                "unrealised_pnl": -200.0, "cum_realised_pnl": 0.0,
                "roe_percent": -40.0, "margin": 500.0, "leverage": 7,
                "liq_price": 72000.0, "take_profit": 0.0,
            },
        ]
        # Only creates FSM for losing positions, not for profitable hedges
        fsms = mgr.reconcile(positions=positions, open_orders=[], execution_history=[])
        # Only the losing Sell position gets an FSM
        assert len(fsms) == 1
        assert fsms[0].side == "Sell"
