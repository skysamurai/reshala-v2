"""DeepSeek AI provider — real API calls with battle-tested prompts."""
import logging
from ai.providers.base import BaseProvider
from ai.prompts import get_system_prompt, build_user_message, parse_response

log = logging.getLogger(__name__)


class DeepSeekProvider(BaseProvider):
    """Calls DeepSeek API (OpenAI-compatible) for trading decisions.

    Uses prompts ported from reshala v1 — 6 strategies, direction filters,
    risk rules, absolute prohibitions.
    """

    def __init__(self, api_key: str = "", model: str = "deepseek-chat", base_url: str = "https://api.deepseek.com"):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._client = None

    def _get_client(self):
        if self._client is None and self._api_key:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    async def decide(
        self,
        symbol: str,
        position: dict | None,
        history: list,
        technical: dict | None = None,
        market: dict | None = None,
        balance: float = 0.0,
    ) -> dict:
        """Make a trading decision using DeepSeek API."""
        if position is None:
            return {"strategy": "WAIT", "reasoning": "no position data", "order": {"side": None, "qty_usd": 0}}

        # Quick guard: position recovered → close
        upnl = position.get("unrealised_pnl", 0)
        if upnl >= 0:
            return {"strategy": "CLOSE", "reasoning": "position recovered — PnL >= 0", "order": {"side": None, "qty_usd": 0}}

        client = self._get_client()
        if client is None:
            # No API key — fallback to conservative WAIT
            log.warning("DeepSeek: no API key configured, returning WAIT")
            return {"strategy": "WAIT", "reasoning": "AI not configured (no API key)", "order": {"side": None, "qty_usd": 0}}

        side = position.get("side", "Sell")
        system_prompt = get_system_prompt(side)
        user_message = build_user_message(
            position=position,
            technical=technical or {},
            funding_rate=(market or {}).get("funding_rate", 0.0),
            orderbook=(market or {}).get("orderbook"),
            available_balance=balance,
            history=history,
        )

        try:
            response = client.chat.completions.create(
                model=self._model,
                max_tokens=1024,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            text = response.choices[0].message.content.strip()
            decision = parse_response(text)
            log.info("DeepSeek: %s → %s", symbol, decision.get("strategy", "?"))
            return decision
        except Exception as e:
            log.error("DeepSeek API error for %s: %s", symbol, e)
            return {"strategy": "WAIT", "reasoning": f"API error: {e}", "order": {"side": None, "qty_usd": 0}}
