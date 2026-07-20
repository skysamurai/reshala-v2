"""Tests for AI prompts."""
from ai.prompts import (
    get_system_prompt, build_user_message, parse_response,
    SYSTEM_PROMPT_SHORT, SYSTEM_PROMPT_LONG,
)


class TestPrompts:
    def test_get_short_prompt_for_sell(self):
        prompt = get_system_prompt("Sell")
        assert "recover the losing short position" in prompt
        assert "DCA_SHORT" in prompt
        assert "SHORT_PUMP" in prompt
        assert "HEDGE_LONG" in prompt

    def test_get_long_prompt_for_buy(self):
        prompt = get_system_prompt("Buy")
        assert "recover the losing long position" in prompt
        assert "DCA_LONG" in prompt
        assert "LONG_DUMP" in prompt
        assert "HEDGE_SHORT" in prompt

    def test_parse_json_response(self):
        text = '{"strategy": "DCA_SHORT", "reasoning": "RSI 15m = 55, good entry", "order": {"side": "Sell", "qty_usd": 12.0, "leverage": 7, "take_profit_percent": 0.3, "stop_loss_percent": 0.0}, "wait_minutes": 0}'
        result = parse_response(text)
        assert result["strategy"] == "DCA_SHORT"
        assert result["order"]["side"] == "Sell"

    def test_parse_json_with_markdown_block(self):
        text = '```json\n{"strategy": "WAIT", "reasoning": "RSI too low", "order": {"side": null}, "wait_minutes": 5}\n```'
        result = parse_response(text)
        assert result["strategy"] == "WAIT"
        assert result["wait_minutes"] == 5

    def test_parse_json_with_plain_code_block(self):
        text = '```\n{"strategy": "SCALP", "reasoning": "oversold bounce", "order": {"side": "Buy", "qty_usd": 10.0, "leverage": 7, "take_profit_percent": 4.0, "stop_loss_percent": 1.5}, "wait_minutes": 0}\n```'
        result = parse_response(text)
        assert result["strategy"] == "SCALP"

    def test_build_user_message_for_short(self):
        pos = {
            "symbol": "BTCUSDT", "side": "Sell", "size": 0.01,
            "avg_price": 65000.0, "mark_price": 67000.0,
            "unrealised_pnl": -200.0, "roe_percent": -40.0,
            "leverage": 7, "margin": 500.0, "liq_price": 72000.0,
        }
        msg = build_user_message(pos, available_balance=200.0)
        assert "BTCUSDT" in msg
        assert "SHORT" in msg
        assert "65000" in msg
        assert "67000" in msg
        assert "-200.00" in msg
        assert "200.00" in msg  # balance

    def test_build_user_message_for_long(self):
        pos = {
            "symbol": "ETHUSDT", "side": "Buy", "size": 0.1,
            "avg_price": 3200.0, "mark_price": 3100.0,
            "unrealised_pnl": -100.0, "roe_percent": -20.0,
            "leverage": 7, "margin": 500.0, "liq_price": 2800.0,
        }
        msg = build_user_message(pos, available_balance=300.0)
        assert "ETHUSDT" in msg
        assert "LONG" in msg
        assert "3200" in msg

    def test_absolute_prohibition_in_short_prompt(self):
        assert "NEVER suggest closing" in SYSTEM_PROMPT_SHORT
        assert "ABSOLUTE PROHIBITION" in SYSTEM_PROMPT_SHORT

    def test_absolute_prohibition_in_long_prompt(self):
        assert "NEVER suggest closing" in SYSTEM_PROMPT_LONG
        assert "ABSOLUTE PROHIBITION" in SYSTEM_PROMPT_LONG
