import pytest
from exchange.reconnect import ReconnectPolicy


class TestReconnectPolicy:
    def test_exponential_backoff(self):
        policy = ReconnectPolicy()
        delays = [policy.next() for _ in range(7)]
        assert delays == [1, 2, 5, 10, 30, 60, 60]

    def test_reset(self):
        policy = ReconnectPolicy()
        policy._attempt = 5
        policy.reset()
        assert policy._attempt == 0
