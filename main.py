#!/usr/bin/env python3
"""Reshala v2 entry point — wires domain + exchange + AI + bus together.

Usage:
    python main.py                          # dry-run (no orders)
    python main.py --symbols BTCUSDT,ETHUSDT
"""
import asyncio
import logging
import sys

from engine.bus.event_bus import EventBus
from engine.bus.command_bus import CommandBus
from engine.trading_engine import TradingEngine
from exchange.adapter import ExchangeAdapter
from exchange.mcp_client import McpClient
from exchange.streams.manager import StreamManager
from ai.service import AIService
from ai.providers.deepseek import DeepSeekProvider
from domain.events import EventType, AICompleted, OrderFilled, OrderRejected
from domain.events import PositionChanged

log = logging.getLogger(__name__)


async def main(symbols: list[str], trade: bool = False):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    # ─── MCP client ───────────────────────────────────────
    # In Claude Code: use mcp__bybit__* tools directly
    # In production: replace with tool dispatcher
    mcp = McpClient()
    log.info("MCP client created (test mode — no orders)")

    # ─── Buses ────────────────────────────────────────────
    bus = EventBus()
    cmd_bus = CommandBus()
    log.info("EventBus + CommandBus started")

    # ─── Adapter ──────────────────────────────────────────
    adapter = ExchangeAdapter(mcp) if trade else ExchangeAdapter()
    cmd_bus.subscribe(type("OrderCommand", (), {}), lambda cmd: adapter.place_order(cmd))

    # ─── AI ───────────────────────────────────────────────
    ai = AIService(bus, provider=DeepSeekProvider())

    # ─── Engine ───────────────────────────────────────────
    engine = TradingEngine(bus, cmd_bus, adapter, ai, symbols=symbols)

    # Subscribe engine event handlers
    bus.subscribe(EventType.AI_COMPLETED, engine.on_ai_completed)
    bus.subscribe(EventType.ORDER_FILLED, engine.on_order_filled)
    bus.subscribe(EventType.ORDER_REJECTED, engine.on_order_rejected)
    bus.subscribe(EventType.POSITION_CHANGED, engine.on_position_changed)

    # ─── Streams ──────────────────────────────────────────
    stream_mgr = StreamManager(bus, mcp, symbols)

    try:
        # Start streams first
        await stream_mgr.start_all()
        log.info("Streams started for %d symbols: %s", len(symbols), symbols)

        # Run engine
        await engine.run()

    except KeyboardInterrupt:
        log.info("Shutting down...")
    finally:
        await stream_mgr.stop_all()
        await engine.shutdown()
        await bus.shutdown()
        log.info("Reshala v2 stopped")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Reshala v2 — Trading Engine")
    p.add_argument("--symbols", default="BTCUSDT", help="Comma-separated symbols")
    p.add_argument("--trade", action="store_true", help="Enable real orders (DANGER)")
    args = p.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",")]
    asyncio.run(main(symbols, trade=args.trade))
