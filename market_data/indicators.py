"""Technical indicators — pure math, no exchange dependency.

RSI, EMA, ATR, MACD computed from kline data.
All functions accept price lists and return float or None (if insufficient data).
"""
import math


def rsi(prices: list[float], period: int = 14) -> float | None:
    """Relative Strength Index. Returns 0-100 or None."""
    if len(prices) < period + 1:
        return None

    gains = 0.0
    losses = 0.0

    for i in range(1, period + 1):
        diff = prices[i] - prices[i - 1]
        if diff > 0:
            gains += diff
        else:
            losses -= diff

    avg_gain = gains / period
    avg_loss = losses / period

    if avg_loss == 0:
        return 100.0

    for i in range(period + 1, len(prices)):
        diff = prices[i] - prices[i - 1]
        gain = max(diff, 0)
        loss = max(-diff, 0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def ema(prices: list[float], period: int = 10) -> float | None:
    """Exponential Moving Average. Returns latest EMA value or None."""
    if len(prices) < period:
        return None

    multiplier = 2.0 / (period + 1)
    ema_val = sum(prices[:period]) / period  # SMA for initial

    for price in prices[period:]:
        ema_val = (price - ema_val) * multiplier + ema_val

    return ema_val


def ema_series(prices: list[float], period: int = 10) -> list[float]:
    """Full EMA series."""
    if len(prices) < period:
        return []
    multiplier = 2.0 / (period + 1)
    result = [sum(prices[:period]) / period]
    for price in prices[period:]:
        result.append((price - result[-1]) * multiplier + result[-1])
    return result


def atr(highs: list[float], lows: list[float], closes: list[float],
        period: int = 14) -> float | None:
    """Average True Range. Returns volatility measure or None."""
    n = min(len(highs), len(lows), len(closes))
    if n < period + 1:
        return None

    true_ranges = []
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        true_ranges.append(tr)

    atr_val = sum(true_ranges[:period]) / period

    for i in range(period, len(true_ranges)):
        atr_val = (atr_val * (period - 1) + true_ranges[i]) / period

    return atr_val


def macd(prices: list[float], fast: int = 12, slow: int = 26,
         signal: int = 9) -> dict | None:
    """MACD indicator. Returns {macd_line, signal, histogram} or None."""
    if len(prices) < slow + signal:
        return None

    ema_fast = ema_series(prices, fast)
    ema_slow = ema_series(prices, slow)

    # Align series lengths
    offset = slow - fast
    macd_line = [ema_fast[i + offset] - ema_slow[i] for i in range(len(ema_slow))]

    signal_line_series = ema_series(macd_line, signal)
    if not signal_line_series:
        return None

    latest_macd = macd_line[-1]
    latest_signal = signal_line_series[-1]

    return {
        "macd_line": round(latest_macd, 6),
        "signal": round(latest_signal, 6),
        "histogram": round(latest_macd - latest_signal, 6),
    }


def compute_all(klines: list[dict]) -> dict:
    """Compute all indicators from kline data. Returns dict for AI prompt.

    klines: list of {"high": str, "low": str, "close": str} from Bybit
    """
    closes = [float(k["close"]) for k in klines]
    highs = [float(k["high"]) for k in klines]
    lows = [float(k["low"]) for k in klines]

    result = {
        "rsi": rsi(closes, 14),
        "ema_10": ema(closes, 10),
        "ema_20": ema(closes, 20),
        "atr": atr(highs, lows, closes, 14),
        "macd": macd(closes),
        "close_count": len(closes),
    }

    # Price context
    if closes:
        result["last_close"] = closes[-1]
        result["close_1m_ago"] = closes[-2] if len(closes) > 1 else closes[-1]
        if len(closes) >= 5:
            result["close_5m_ago"] = closes[-5]

    return result
