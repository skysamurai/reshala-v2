"""Shared test fixtures for reshala-v2 tests."""
import pytest
from dataclasses import dataclass
from typing import Optional


@dataclass
class MockPosition:
    """Minimal position representation for tests."""
    symbol: str
    side: str  # "Buy" or "Sell"
    size: float
    avg_price: float
    mark_price: float
    unrealised_pnl: float
    cum_realised_pnl: float
    roe_percent: float
    margin: float
    leverage: int
    liq_price: float
    take_profit: float = 0.0


@pytest.fixture
def btc_short():
    """Standard BTC short position for testing."""
    return MockPosition(
        symbol="BTCUSDT",
        side="Sell",
        size=0.01,
        avg_price=65000.0,
        mark_price=67000.0,
        unrealised_pnl=-200.0,
        cum_realised_pnl=0.0,
        roe_percent=-40.0,
        margin=500.0,
        leverage=7,
        liq_price=72000.0,
    )


@pytest.fixture
def eth_long():
    """Standard ETH long position for testing."""
    return MockPosition(
        symbol="ETHUSDT",
        side="Buy",
        size=0.1,
        avg_price=3200.0,
        mark_price=3100.0,
        unrealised_pnl=-100.0,
        cum_realised_pnl=0.0,
        roe_percent=-20.0,
        margin=500.0,
        leverage=7,
        liq_price=2800.0,
    )
