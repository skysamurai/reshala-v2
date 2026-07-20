"""MCP Client — thin wrapper over mcp__bybit__* tool calls.

Provides the interface that streams and ExchangeAdapter expect.
"""
import logging

log = logging.getLogger(__name__)


class McpClient:
    """Wraps mcp__bybit__* MCP tools. Used by streams (WS) and adapter (REST).

    Accepts a callable `invoke(tool_name, **params)` that calls the MCP tool.
    In Claude Code: invoke = lambda name, **kw: mcp__bybit__<name>(**kw)
    In production: a tool dispatcher.
    """

    def __init__(self, invoker=None):
        self._invoke = invoker or self._noop

    async def _noop(self, tool, **kwargs):
        log.debug("MCP noop: %s(%s)", tool, kwargs)
        return {}

    # ─── WebSocket subscriptions ──────────────────────────

    async def start_subscription(self, category: str, topic: str) -> str:
        """Open a persistent WS subscription. Returns subscription_id."""
        result = await self._invoke("startSubscription", category=category, topic=topic,
                                    maxMessages=500)
        return result.get("subscriptionId", "")

    async def read_messages(self, sub_id: str, limit: int = 50) -> list[dict]:
        """Read buffered messages from a subscription."""
        result = await self._invoke("readMessages", subscriptionId=sub_id, limit=limit)
        return result.get("messages", [])

    async def stop_subscription(self, sub_id: str) -> None:
        await self._invoke("stopSubscription", subscriptionId=sub_id)

    # ─── REST: Orders ─────────────────────────────────────

    async def create_order(self, **params) -> dict:
        """Place an order on Bybit. Returns full response dict."""
        return await self._invoke("createOrder", **params)

    async def cancel_order(self, **params) -> dict:
        return await self._invoke("cancelOrder", **params)

    async def cancel_all_orders(self, **params) -> None:
        await self._invoke("cancelAllOrders", **params)

    # ─── REST: Queries ────────────────────────────────────

    async def get_position_info(self, **params) -> dict:
        return await self._invoke("getPositionInfo", **params)

    async def get_open_orders(self, **params) -> dict:
        return await self._invoke("getOpenOrders", **params)

    async def get_wallet_balance(self, **params) -> dict:
        return await self._invoke("getWalletBalance", **params)

    async def get_instruments_info(self, **params) -> dict:
        return await self._invoke("getInstrumentsInfo", **params)
