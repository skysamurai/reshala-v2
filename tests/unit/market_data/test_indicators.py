"""Tests for technical indicators — pure math, no exchange needed."""
import pytest
from market_data.indicators import rsi, ema, atr, macd, compute_all


class TestRSI:
    def test_rsi_oversold(self):
        # 14 periods of down moves → RSI near 0
        prices = [100.0 - i * 0.1 for i in range(20)]
        result = rsi(prices, period=14)
        assert result < 30  # oversold

    def test_rsi_overbought(self):
        # 14 periods of up moves → RSI near 100
        prices = [100.0 + i * 0.5 for i in range(20)]
        result = rsi(prices, period=14)
        assert result > 70  # overbought

    def test_rsi_neutral(self):
        # Alternating up/down → RSI near 50
        prices = [100.0, 101.0, 99.0, 102.0, 98.0, 103.0, 97.0, 104.0,
                  96.0, 105.0, 95.0, 106.0, 94.0, 107.0, 93.0, 108.0]
        result = rsi(prices, period=14)
        assert 40 <= result <= 60

    def test_rsi_not_enough_data(self):
        result = rsi([100.0, 101.0, 102.0], period=14)
        assert result is None


class TestEMA:
    def test_ema_smoothed(self):
        prices = list(range(1, 21))  # 1..20, uptrend
        ema10 = ema(prices, period=10)
        assert ema10 is not None
        assert ema10 > prices[-1] * 0.5  # should be reasonable

    def test_ema_not_enough_data(self):
        result = ema([1.0, 2.0, 3.0], period=10)
        assert result is None


class TestATR:
    def test_atr_volatile(self):
        highs = [100.0 + i for i in range(20)]
        lows = [90.0 + i for i in range(20)]
        closes = [95.0 + i for i in range(20)]
        result = atr(highs, lows, closes, period=14)
        assert result is not None
        assert result >= 10.0  # TR = high-low = 10 each period

    def test_atr_not_enough_data(self):
        result = atr([1.0, 2.0], [0.0, 1.0], [0.5, 1.5], period=14)
        assert result is None


class TestMACD:
    def test_macd_uptrend(self):
        # Exponential-ish uptrend creates clear MACD/signal divergence
        prices = [100.0]
        for i in range(1, 60):
            prices.append(prices[-1] * 1.005)  # 0.5% per period
        result = macd(prices)
        assert result is not None
        assert result["macd_line"] > result["signal"]  # MACD above signal = bullish

    def test_macd_not_enough_data(self):
        prices = list(range(1, 20))
        result = macd(prices)
        assert result is None


class TestComputeAll:
    def test_compute_all_from_klines(self):
        klines = [
            {"high": str(100.0 + i), "low": str(95.0 + i), "close": str(97.0 + i)}
            for i in range(50)
        ]
        result = compute_all(klines)
        assert result["rsi"] is not None
        assert result["ema_10"] is not None
        assert result["ema_20"] is not None
        assert result["atr"] is not None
        assert result["macd"] is not None
        assert "macd_line" in result["macd"]
        assert "signal" in result["macd"]
        assert result["close_count"] == 50
