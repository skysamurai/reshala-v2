"""Replay tests — snapshot + event log → full state recovery."""
import json
import os
import tempfile
import pytest
from domain.exchange_state import ExchangeState
from domain.events import PositionChanged, PriceUpdate
from domain.events.serialization import EventSerializer
from domain.recovery.replay import ReplayEngine


class TestReplay:
    def test_replay_from_snapshot_and_log(self):
        tmp = tempfile.mkdtemp()
        snap_path = os.path.join(tmp, "snapshot.json")
        log_path = os.path.join(tmp, "events.jsonl")
        serializer = EventSerializer()

        # Build initial state
        state = ExchangeState()
        state.apply(PositionChanged(symbol="BTCUSDT", side="Sell", size=0.01, unrealised_pnl=-200.0))
        state.apply(PositionChanged(symbol="ETHUSDT", side="Sell", size=0.1, unrealised_pnl=-300.0))

        # Save snapshot
        with open(snap_path, "w") as f:
            json.dump(state.snapshot(), f)

        # Write additional events to log
        events = [
            PositionChanged(symbol="BTCUSDT", side="Sell", size=0.02, unrealised_pnl=-400.0, margin=1000.0,
                          roe_percent=-40.0, liq_price=72000.0),
            PriceUpdate(symbol="BTCUSDT", price=67100.0, high=67200.0, low=67000.0, volume=500.0),
        ]
        with open(log_path, "a") as f:
            for e in events:
                f.write(serializer.to_json(e) + "\n")

        # Replay
        engine = ReplayEngine()
        recovered = engine.replay(snap_path, log_path)

        # Verify recovered state
        assert recovered.get_position("BTCUSDT") is not None
        assert recovered.get_position("BTCUSDT")["size"] == 0.02
        assert recovered.get_position("BTCUSDT")["unrealised_pnl"] == -400.0
        assert recovered.get_position("ETHUSDT") is not None  # from snapshot
        assert recovered.version > state.version  # events applied

    def test_serializer_roundtrip(self):
        """Event → JSON → Event = identical."""
        serializer = EventSerializer()
        original = PositionChanged(
            symbol="BTCUSDT", side="Sell", size=0.01,
            unrealised_pnl=-200.0, margin=500.0,
            roe_percent=-40.0, liq_price=72000.0,
        )
        json_line = serializer.to_json(original)
        restored = serializer.from_json(json_line)

        assert restored.symbol == original.symbol
        assert restored.side == original.side
        assert restored.size == original.size
        assert restored.unrealised_pnl == original.unrealised_pnl
