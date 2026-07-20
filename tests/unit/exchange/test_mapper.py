from exchange.mapper import to_price_update, to_position_changed, to_order_filled


class TestMapper:
    def test_to_price_update(self):
        raw = {"symbol": "BTCUSDT", "lastPrice": "67000.0", "highPrice24h": "67100.0",
               "lowPrice24h": "66900.0", "volume24h": "100.0"}
        event = to_price_update(raw)
        assert event.symbol == "BTCUSDT"
        assert event.price == 67000.0
        assert event.source == "bybit_ws"

    def test_to_position_changed(self):
        raw = {"symbol": "BTCUSDT", "side": "Sell", "size": "0.01",
               "positionIM": "500.0", "unrealisedPnl": "-200.0",
               "cumRealisedPnl": "0.0", "liqPrice": "72000.0"}
        event = to_position_changed(raw)
        assert event.symbol == "BTCUSDT"
        assert event.size == 0.01
        assert event.unrealised_pnl == -200.0

    def test_to_order_filled(self):
        raw = {"orderId": "ord_1", "orderLinkId": "BTCUSDT_DCA_1",
               "symbol": "BTCUSDT", "side": "Sell", "execQty": "0.005", "execPrice": "67200.0"}
        event = to_order_filled(raw)
        assert event.order_id == "ord_1"
        assert event.qty == 0.005
