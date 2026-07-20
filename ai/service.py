"""AIService — async AI decision lifecycle. TradingEngine doesn't know about LLM.

Flow: Engine.request_decision() → AIService → provider.decide() → AICompleted → EventBus
"""
import asyncio
import logging
import uuid
from domain.events import AICompleted
from domain.fsm.position_fsm import PositionFSM
from domain.exchange_state import ExchangeState

log = logging.getLogger(__name__)


class AIService:
    """Pluggable AI decision service. Provider can be DeepSeek, Claude, etc."""

    def __init__(self, bus, provider=None):
        self._bus = bus
        self._provider = provider

    async def request_decision(self, fsm: PositionFSM, state: ExchangeState) -> None:
        """Request AI decision asynchronously. Result comes as AICompleted event."""
        correlation_id = uuid.uuid4().hex

        if not self._provider:
            log.debug("No AI provider configured — skipping decision for %s", fsm.symbol)
            return

        pos = state.get_position(fsm.symbol)
        history = state.get_position_history(fsm.symbol, limit=50)

        # Launch async — don't block the engine
        balance = state.get_balance("USDT")
        asyncio.create_task(self._call_provider(
            fsm.symbol, fsm.state_version, pos, history, correlation_id, balance
        ))

    async def _call_provider(
        self, symbol: str, state_version: int,
        position: dict | None, history: list, correlation_id: str,
        balance: float = 0.0,
    ) -> None:
        try:
            decision = await self._provider.decide(
                symbol=symbol,
                position=position,
                history=history,
                technical=None,
                market=None,
                balance=balance,
            )
            event = AICompleted(
                symbol=symbol,
                decision=decision,
                operation_id=correlation_id,
                state_version=state_version,
                correlation_id=correlation_id,
            )
            await self._bus.publish(event)
            log.info("AI decision for %s: %s", symbol, decision.get("strategy", "?"))
        except Exception:
            log.exception("AI provider failed for %s", symbol)
