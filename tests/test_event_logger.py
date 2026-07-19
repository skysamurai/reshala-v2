"""Tests for EventLogger — JSONL black box recorder."""
import json
import os
import tempfile
import pytest
from engine.event_logger import EventLogger
from engine.fsm.states import FSMState


class TestEventLogger:
    @pytest.mark.asyncio
    async def test_logs_transition_to_jsonl(self):
        log_path = os.path.join(tempfile.mkdtemp(), "events.jsonl")
        logger = EventLogger(log_path)

        await logger.log_transition(
            symbol="BTCUSDT",
            from_state=FSMState.IDLE,
            to_state=FSMState.PREPARING,
            trigger="AICompleted",
            reason="AI recommended DCA_SHORT",
            operation_id="op_abc",
            order_link_id=None,
            state_version=42,
        )
        await logger.close()

        with open(log_path, "r") as f:
            lines = f.readlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["symbol"] == "BTCUSDT"
        assert data["from_state"] == "idle"
        assert data["to_state"] == "preparing"
        assert data["state_version"] == 42
        assert data["event_id"]
        assert data["ts"]

    @pytest.mark.asyncio
    async def test_logs_multiple_events(self):
        log_path = os.path.join(tempfile.mkdtemp(), "events.jsonl")
        logger = EventLogger(log_path)

        for i in range(5):
            await logger.log_transition(
                symbol="BTCUSDT",
                from_state=FSMState.IDLE,
                to_state=FSMState.PREPARING,
                trigger="TimerTick",
                reason=f"cycle {i}",
                operation_id=f"op_{i}",
                order_link_id=None,
                state_version=i,
            )
        await logger.close()

        with open(log_path, "r") as f:
            lines = f.readlines()
        assert len(lines) == 5
        versions = [json.loads(l)["state_version"] for l in lines]
        assert versions == [0, 1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_state_version_is_unique_event_id(self):
        log_path = os.path.join(tempfile.mkdtemp(), "events.jsonl")
        logger = EventLogger(log_path)

        await logger.log_transition(
            symbol="ETHUSDT", from_state=FSMState.IDLE, to_state=FSMState.PREPARING,
            trigger="AICompleted", reason="test", operation_id="op_x",
            order_link_id=None, state_version=1,
        )
        await logger.close()

        with open(log_path, "r") as f:
            data = json.loads(f.readline())
        assert len(data["event_id"]) > 0
