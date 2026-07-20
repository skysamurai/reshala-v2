"""ExchangeAdapter — thin MCP wrapper. NO business logic."""
import logging
from domain.commands.order import OrderCommand
from domain.commands.cancel import CancelCommand

log = logging.getLogger(__name__)


class ExchangeAdapter:
    """Executes commands against Bybit. Queries exchange state.

    Rule: NEVER makes trading decisions. Only executes commands.
    """

    def __init__(self, mcp=None):
        self._mcp = mcp
        self._rate_limiter = None  # Semaphore(10) for production

    # ─── Commands ─────────────────────────────────────────

    async def place_order(self, cmd: OrderCommand) -> dict:
        """Execute an order on Bybit via MCP."""
        if not self._mcp:
            log.warning("No MCP configured — order not sent: %s %s %s",
                        cmd.symbol, cmd.side, cmd.qty)
            return {"retCode": -1, "retMsg": "No MCP (test mode)"}

        params = dict(
            category="linear",
            symbol=cmd.symbol,
            side=cmd.side,
            orderType="Market" if not cmd.price else "Limit",
            qty=cmd.qty,
            orderLinkId=cmd.order_link_id,
            reduceOnly=cmd.reduce_only,
        )
        if cmd.price:
            params["price"] = cmd.price
            params["timeInForce"] = "GTC"
        if cmd.tp_price:
            params["takeProfit"] = cmd.tp_price
        if cmd.sl_price:
            params["stopLoss"] = cmd.sl_price

        log.info("ORDER %s %s qty=%s price=%s id=%s",
                 cmd.symbol, cmd.side, cmd.qty, cmd.price or "market", cmd.order_link_id)
        return await self._mcp.create_order(**params)

    async def cancel_order(self, cmd: CancelCommand) -> dict:
        if not self._mcp:
            return {"retCode": -1, "retMsg": "No MCP (test mode)"}
        return await self._mcp.cancel_order(
            category="linear", symbol=cmd.symbol,
            orderId=cmd.order_id, orderLinkId=cmd.order_link_id,
        )

    async def cancel_all_orders(self, symbol: str) -> None:
        if self._mcp:
            await self._mcp.cancel_all_orders(category="linear", symbol=symbol)

    # ─── Queries ──────────────────────────────────────────

    async def fetch_positions(self) -> list[dict]:
        if not self._mcp:
            return []
        resp = await self._mcp.get_position_info(category="linear", settleCoin="USDT")
        return resp.get("result", {}).get("list", [])

    async def fetch_open_orders(self, symbol: str = None) -> list[dict]:
        if not self._mcp:
            return []
        params = dict(category="linear")
        if symbol:
            params["symbol"] = symbol
        resp = await self._mcp.get_open_orders(**params)
        return resp.get("result", {}).get("list", [])

    async def fetch_balance(self, coin: str = "USDT") -> dict:
        if not self._mcp:
            return {}
        resp = await self._mcp.get_wallet_balance(accountType="UNIFIED", coin=coin)
        wallets = resp.get("result", {}).get("list", [])
        return wallets[0] if wallets else {}
