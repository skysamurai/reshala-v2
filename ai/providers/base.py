"""Base AI provider interface."""
from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Provider decides what trade to make. Result is published as AICompleted."""

    @abstractmethod
    async def decide(self, symbol: str, position: dict | None, history: list,
                     technical: dict | None = None, market: dict | None = None,
                     balance: float = 0.0) -> dict:
        """Return {"strategy": "...", "reasoning": "...", "order": {...}, "wait_minutes": 0}."""
        ...
