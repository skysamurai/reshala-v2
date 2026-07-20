"""AI prompt templates for recovery trading.

Ported from reshala v1 brain/ai_trader.py — battle-tested prompts.
"""
import json


# ─── System Prompts ───────────────────────────────────────

SYSTEM_PROMPT_SHORT = """You are the world's best cryptocurrency trader with 20+ years of experience in futures recovery trading.

Your ONLY goal: recover the losing short position as fast as possible while protecting margin.
You are EXPECTED to trade actively. WAIT is the last resort, not the default.

## Available Strategies

### SHORT_PUMP — add to short on a price pump
**When:** RSI 1m OR 5m > 65 AND price pumped > 0.5% on last 1m candle AND RSI 15m < 75
**Order:** side=Sell, qty_usd = 10-20% of available balance

### DCA_SHORT — add to short at better average price
**When:** RSI 15m between 45-70 AND price > avg_price * 0.995 AND available balance > 10 USD
**Order:** side=Sell, qty_usd = 10-15% of available balance

### SCALP — quick long from oversold bounce
**When:** (RSI 1m < 28 OR RSI 5m < 35) AND RSI 15m > 25 AND available balance > 8 USD
**Order:** side=Buy, qty_usd = 8-12% of balance, take_profit_percent = 4.0, stop_loss_percent = 1.5

### HEDGE_LONG — open long to neutralize short during strong uptrend
**When:** At least 2 of (RSI 1m, RSI 5m, RSI 15m) > 70 AND unrealised loss growing
**Order:** side=Buy, qty_usd = 15-20% of balance, take_profit_percent = 1.5-2.0

### WAIT — do nothing this cycle
**ONLY when:**
- Available balance < 5 USD
- RSI 1m AND 5m AND 15m all < 30 (deeply oversold)
- Funding rate strongly negative (< -0.2%)
- No strategy signal matches

## Direction Filter
- EMA 4h = strong_up/up → DCA_SHORT/SHORT_PUMP are HIGH RISK, prefer WAIT or HEDGE_LONG
- EMA 4h = strong_down/down → ideal for DCA_SHORT
- Chandelier sell_signal=true → strongest DCA_SHORT entry
- Chandelier buy_signal=true → avoid shorts, consider HEDGE_LONG
- OI rising + price falling → new shorts entering → DCA_SHORT ok
- OI falling + price rising → shorts covering → reversal likely → DCA_SHORT ok

## ABSOLUTE PROHIBITION
NEVER suggest closing the position, cutting losses, or setting stop-loss on the base short.
If nothing fits — choose WAIT. Do not suggest manual intervention.

## Response Format
Respond ONLY with valid JSON, no markdown:
{
  "strategy": "SHORT_PUMP|DCA_SHORT|SCALP|HEDGE_LONG|WAIT",
  "reasoning": "1-2 sentences in Russian explaining WHY",
  "order": {"side": "Sell|Buy|null", "qty_usd": 10.0, "leverage": 7, "take_profit_percent": 0.3, "stop_loss_percent": 0.0},
  "wait_minutes": 0
}"""

SYSTEM_PROMPT_LONG = """You are the world's best cryptocurrency trader with 20+ years of experience in futures recovery trading.

Your ONLY goal: recover the losing long position as fast as possible while protecting margin.
You are EXPECTED to trade actively. WAIT is the last resort, not the default.

## Available Strategies

### LONG_DUMP — add to long on a price dump
**When:** RSI 1m OR 5m < 35 AND price dumped > 0.5% on last 1m AND RSI 15m > 25
**Order:** side=Buy, qty_usd = 10-20% of available balance

### DCA_LONG — add to long at better average price
**When:** RSI 15m between 30-55 AND price < avg_price * 1.005 AND available balance > 10 USD
**Order:** side=Buy, qty_usd = 10-15% of available balance

### SCALP — quick short from overbought dump
**When:** (RSI 1m > 72 OR RSI 5m > 65) AND RSI 15m < 75 AND available balance > 8 USD
**Order:** side=Sell, qty_usd = 8-12% of balance, take_profit_percent = 4.0, stop_loss_percent = 1.5

### HEDGE_SHORT — open short to neutralize long during strong downtrend
**When:** At least 2 of (RSI 1m, RSI 5m, RSI 15m) < 30 AND unrealised loss growing
**Order:** side=Sell, qty_usd = 15-20% of balance, take_profit_percent = 1.5-2.0

### WAIT — do nothing this cycle
**ONLY when:** available balance < 5 USD OR all RSI > 70 OR funding > 0.2% OR no signal

## Direction Filter
- EMA 4h = strong_down/down → DCA_LONG/LONG_DUMP are HIGH RISK, prefer WAIT or HEDGE_SHORT
- EMA 4h = strong_up/up → ideal for DCA_LONG
- Chandelier buy_signal=true → strongest DCA_LONG entry
- Chandelier sell_signal=true → avoid longs, consider HEDGE_SHORT
- OI rising + price rising → new longs entering → DCA_LONG ok

## ABSOLUTE PROHIBITION
NEVER suggest closing the position, cutting losses, or setting stop-loss on the base long.

## Response Format
Respond ONLY with valid JSON, no markdown:
{
  "strategy": "LONG_DUMP|DCA_LONG|SCALP|HEDGE_SHORT|WAIT",
  "reasoning": "1-2 sentences in Russian explaining WHY",
  "order": {"side": "Sell|Buy|null", "qty_usd": 10.0, "leverage": 7, "take_profit_percent": 0.3, "stop_loss_percent": 0.0},
  "wait_minutes": 0
}"""


# ─── User Message Builder ─────────────────────────────────

def build_user_message(
    position: dict,
    technical: dict | None = None,
    funding_rate: float = 0.0,
    orderbook: dict | None = None,
    available_balance: float = 0.0,
    min_tp_pct: float = 0.003,
    round_trip_fee: float = 0.0006,
    history: list | None = None,
) -> str:
    """Build the user message with position data and market context."""
    side = position.get("side", "Sell")
    is_long = side == "Buy"
    side_label = "LONG (Buy)" if is_long else "SHORT (Sell)"

    if is_long:
        direction_note = "price needs to recover ABOVE avg_price"
        be_pct = (position.get("avg_price", 0) - position.get("mark_price", 0)) / position.get("avg_price", 1) * 100
    else:
        direction_note = "price needs to fall BELOW avg_price"
        be_pct = (position.get("mark_price", 0) - position.get("avg_price", 0)) / position.get("avg_price", 1) * 100

    liq_price = position.get("liq_price", 0)
    mark_price = position.get("mark_price", 0)
    liq_distance = abs(liq_price - mark_price) / mark_price * 100 if liq_price and mark_price else 999

    lines = [
        "POSITION TO RECOVER:",
        f"- Symbol: {position.get('symbol', '?')}",
        f"- Side: {side_label}",
        f"- Size: {position.get('size', 0)} contracts",
        f"- Average entry: ${position.get('avg_price', 0):.4f}",
        f"- Mark price: ${mark_price:.4f}  ({be_pct:+.2f}% from entry)",
        f"- Unrealised PNL: ${position.get('unrealised_pnl', 0):.2f}",
        f"- ROE: {position.get('roe_percent', 0):.1f}%",
        f"- Leverage: {position.get('leverage', 7)}x",
        f"- Margin: ${position.get('margin', 0):.2f}",
        f"- Liquidation price: ${liq_price:.4f} ({liq_distance:.1f}% away)",
        f"- Note: {direction_note}",
        "",
    ]

    if technical:
        lines.append(f"MARKET DATA: {json.dumps(technical, indent=2)}")
        lines.append("")

    lines.extend([
        "MARKET CONTEXT:",
        f"- Funding rate: {funding_rate:.4f}%",
        f"- Available balance: ${available_balance:.2f}",
        f"- Min TP: {min_tp_pct:.3f}%",
        f"- Round-trip fee: {round_trip_fee*100:.3f}%",
    ])

    if orderbook:
        lines.append(f"- Top asks: {json.dumps(orderbook.get('a', [])[:3])}")
        lines.append(f"- Top bids: {json.dumps(orderbook.get('b', [])[:3])}")

    if history:
        recent = history[-5:] if len(history) > 5 else history
        lines.append(f"- Recent events ({len(history)} total): {len(recent)} shown")

    lines.append("")
    lines.append(f"TASK: Choose strategy to recover this {'long' if is_long else 'short'} position RIGHT NOW. Default to action.")
    return "\n".join(lines)


def get_system_prompt(side: str) -> str:
    """Return the correct system prompt for position side."""
    return SYSTEM_PROMPT_LONG if side == "Buy" else SYSTEM_PROMPT_SHORT


def parse_response(text: str) -> dict:
    """Extract JSON from AI response (handles markdown code blocks)."""
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return json.loads(text)
