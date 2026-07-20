"""Mapper — converts raw Bybit data to typed domain Events."""
from domain.events import PriceUpdate, PositionChanged
from domain.events import OrderFilled, OrderRejected, OrderCancelled


def to_price_update(raw: dict) -> PriceUpdate:
    return PriceUpdate(
        symbol=raw.get("symbol", ""),
        price=float(raw.get("lastPrice", raw.get("price", 0))),
        high=float(raw.get("highPrice24h", raw.get("high", 0))),
        low=float(raw.get("lowPrice24h", raw.get("low", 0))),
        volume=float(raw.get("volume24h", raw.get("volume", 0))),
        source="bybit_ws",
    )


def to_position_changed(raw: dict) -> PositionChanged:
    return PositionChanged(
        symbol=raw.get("symbol", ""),
        side=raw.get("side", ""),
        size=float(raw.get("size", 0)),
        margin=float(raw.get("positionIM", raw.get("margin", 0))),
        unrealised_pnl=float(raw.get("unrealisedPnl", raw.get("unrealised_pnl", 0))),
        roe_percent=float(raw.get("cumRealisedPnl", raw.get("roe_percent", 0))),
        liq_price=float(raw.get("liqPrice", raw.get("liq_price", 0))),
        source="bybit_ws",
    )


def to_order_filled(raw: dict) -> OrderFilled:
    return OrderFilled(
        order_id=raw.get("orderId", raw.get("order_id", "")),
        order_link_id=raw.get("orderLinkId", raw.get("order_link_id", "")),
        symbol=raw.get("symbol", ""),
        side=raw.get("side", ""),
        qty=float(raw.get("execQty", raw.get("qty", 0))),
        price=float(raw.get("execPrice", raw.get("price", 0))),
        source="bybit_ws",
    )


def to_order_rejected(raw: dict) -> OrderRejected:
    return OrderRejected(
        order_id=raw.get("orderId", raw.get("order_id", "")),
        order_link_id=raw.get("orderLinkId", raw.get("order_link_id", "")),
        symbol=raw.get("symbol", ""),
        reason=raw.get("rejectReason", raw.get("reason", "")),
        source="bybit_ws",
    )


def to_order_cancelled(raw: dict) -> OrderCancelled:
    return OrderCancelled(
        order_id=raw.get("orderId", raw.get("order_id", "")),
        symbol=raw.get("symbol", ""),
        source="bybit_ws",
    )
