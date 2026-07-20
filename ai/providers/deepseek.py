"""DeepSeek AI provider."""
import logging

log = logging.getLogger(__name__)


class DeepSeekProvider:
    """DeepSeek AI decision provider. Implements the AI decision interface."""

    async def decide(self, symbol: str, position: dict | None, history: list) -> dict:
        """Make a trading decision for a losing position.

        Returns: {"strategy": "WAIT"|"DCA_SHORT"|"HEDGE"|..., "reasoning": "..."}

        This is a skeleton — actual LLM call will be implemented in AI prompt epic.
        """
        if position is None:
            return {"strategy": "WAIT", "reasoning": "no position data"}

        upnl = position.get("unrealised_pnl", 0)
        roe = position.get("roe_percent", 0)

        if upnl >= 0:
            return {"strategy": "CLOSE", "reasoning": "position recovered"}

        # Skeleton decision logic — replaced by LLM in AI prompt epic
        return {
            "strategy": "WAIT",
            "reasoning": f"uPNL={upnl:.2f}, ROE={roe:.1f}% — waiting for market signal",
        }
