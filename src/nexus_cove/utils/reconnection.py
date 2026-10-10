from __future__ import annotations

import asyncio
import random


class ExponentialBackoff:
    """Exponential backoff with jitter for reconnection logic."""

    def __init__(
        self,
        base_delay: float = 0.1,
        max_delay: float = 30.0,
        jitter_range: float = 1.0,
    ) -> None:
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter_range = jitter_range
        self.current_delay = base_delay

    async def delay(self) -> None:
        """Wait for the current delay period, then calculate the next delay."""
        await asyncio.sleep(self.current_delay)
        self.current_delay = min(
            self.current_delay * 2 + random.uniform(-self.jitter_range, self.jitter_range),
            self.max_delay,
        )
        self.current_delay = max(0.0, self.current_delay)

    def reset(self) -> None:
        """Reset the delay to the initial value."""
        self.current_delay = self.base_delay
