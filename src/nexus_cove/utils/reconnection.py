from __future__ import annotations

import asyncio
import random
from collections.abc import Callable
from typing import Any


class ExponentialBackoff:
    """Exponential backoff with jitter for reconnection logic."""

    def __init__(
        self,
        base_delay: float = 0.1,  # Start with 100ms
        max_delay: float = 30.0,  # Max 30 seconds
        jitter_range: float = 1.0,  # +/- jitter for randomization
    ) -> None:
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter_range = jitter_range
        self.current_delay = base_delay

    async def delay(self) -> None:
        """Wait for the current delay period, then calculate next delay."""
        await asyncio.sleep(self.current_delay)
        # Exponential backoff with jitter
        self.current_delay = min(
            self.current_delay * 2 + random.uniform(-self.jitter_range, self.jitter_range),
            self.max_delay,
        )
        # Ensure delay doesn't go below zero
        self.current_delay = max(0.0, self.current_delay)

    def reset(self) -> None:
        """Reset the delay to the initial value."""
        self.current_delay = self.base_delay


async def with_exponential_backoff(
    operation: Callable[..., Any],
    *args,
    base_delay: float = 0.1,
    max_delay: float = 30.0,
    max_attempts: int | None = None,
    **kwargs,
) -> Any:
    """
    Execute an operation with exponential backoff retry logic.

    Args:
        operation: Async function to execute
        *args: Arguments to pass to the operation
        base_delay: Initial delay in seconds (default: 0.1s)
        max_delay: Maximum delay in seconds (default: 30.0s)
        max_attempts: Maximum number of attempts (None for infinite)
        **kwargs: Keyword arguments to pass to the operation

    Returns:
        The result of the operation

    Raises:
        The last exception encountered if all attempts fail
    """
    backoff = ExponentialBackoff(base_delay=base_delay, max_delay=max_delay)
    attempt = 0

    while True:
        try:
            return await operation(*args, **kwargs)
        except Exception:
            attempt += 1
            if max_attempts is not None and attempt >= max_attempts:
                raise  # Re-raise the last exception

            # Wait before retrying
            await backoff.delay()
