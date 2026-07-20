"""MarketDataProvider — fetches market data from Bybit for AI decisions.

Returns klines, orderbook, funding rate, open interest.
Feed this into ai.prompts.build_user_message() for accurate AI decisions.
"""
import logging
from market_data.indicators import compute_all

log = logging.getLogger(__name__)


class MarketDataProvider:
    """Provides real market data to AIService. Uses Bybit HTTP client."""

    def __init__(self, client=None):
        self._client = client

    async def get_klines(self, symbol: str, interval: str = "1",
                         limit: int = 100) -> list[dict]:
        """Fetch kline/candlestick data from Bybit."""
        if not self._client:
            return []
        resp = self._client.get_market_kline(
            category="linear", symbol=symbol, interval=interval, limit=limit
        )
        return resp.get("result", {}).get("list", [])

    async def get_orderbook(self, symbol: str, limit: int = 25) -> dict:
        if not self._client:
            return {}
        resp = self._client.get_orderbook(category="linear", symbol=symbol, limit=limit)
        return resp.get("result", {})

    async def get_tickers(self, symbol: str) -> dict:
        if not self._client:
            return {}
        resp = self._client.get_tickers(category="linear", symbol=symbol)
        tickers = resp.get("result", {}).get("list", [])
        return tickers[0] if tickers else {}

    async def get_funding_rate(self, symbol: str) -> float:
        ticker = await self.get_tickers(symbol)
        return float(ticker.get("fundingRate", 0))

    async def get_full_context(self, symbol: str) -> dict:
        """Get everything AI needs for a decision: klines + indicators + orderbook + funding."""
        klines = await self.get_klines(symbol, limit=100)
        indicators = compute_all(klines) if klines else {}
        orderbook = await self.get_orderbook(symbol, limit=5)
        funding_rate = await self.get_funding_rate(symbol)

        return {
            "technical": indicators,
            "market": {
                "funding_rate": funding_rate,
                "orderbook": orderbook,
            },
        }
