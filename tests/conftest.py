"""Global pytest configuration and fixtures for Blind Billion 2.0 tests."""

from __future__ import annotations

from collections.abc import Generator

import pytest

from blindbillion.multiplayer.rate_limiter import global_rate_limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter_before_each_test() -> Generator[None, None, None]:
    """Ensure rate limiter sliding windows are cleared between test executions."""
    global_rate_limiter.reset()
    yield
    global_rate_limiter.reset()
