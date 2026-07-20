"""Tests for CommandBus, OrderCommand, CancelCommand."""
import pytest
from domain.commands.order import OrderCommand
from domain.commands.cancel import CancelCommand
from engine.bus.command_bus import CommandBus


class TestOrderCommand:
    def test_creates_with_required_fields(self):
        cmd = OrderCommand(
            symbol="BTCUSDT", side="Sell", qty="0.005",
            operation_id="op_1", order_link_id="BTCUSDT_DCA_op_1_1",
            sequence=1,
        )
        assert cmd.symbol == "BTCUSDT"
        assert cmd.created_at is not None
        assert cmd.price == ""  # Market by default

    def test_correlation_id_carried(self):
        cmd = OrderCommand(
            symbol="BTCUSDT", side="Sell", qty="0.005",
            correlation_id="corr_abc", operation_id="op_1",
        )
        assert cmd.correlation_id == "corr_abc"


class TestCommandBusDedup:
    @pytest.mark.asyncio
    async def test_blocks_duplicate(self):
        bus = CommandBus()
        executed = []

        async def handler(cmd):
            executed.append(cmd)

        bus.subscribe(OrderCommand, handler)

        cmd = OrderCommand(symbol="BTCUSDT", side="Sell", qty="0.005",
                          operation_id="op_1", sequence=1)
        ok1 = await bus.send(cmd)
        ok2 = await bus.send(cmd)  # duplicate

        assert ok1 is True
        assert ok2 is False  # blocked
        assert len(executed) == 1

    @pytest.mark.asyncio
    async def test_different_sequence_passes(self):
        bus = CommandBus()
        executed = []

        async def handler(cmd):
            executed.append(cmd)

        bus.subscribe(OrderCommand, handler)

        cmd1 = OrderCommand(symbol="BTCUSDT", side="Sell", qty="0.005",
                           operation_id="op_1", sequence=1)
        cmd2 = OrderCommand(symbol="BTCUSDT", side="Sell", qty="0.005",
                           operation_id="op_1", sequence=2)

        assert await bus.send(cmd1) is True
        assert await bus.send(cmd2) is True
        assert len(executed) == 2
