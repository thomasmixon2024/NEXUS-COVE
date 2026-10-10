"""Turn-limit guard for direct-message replies between agents.

Rules:
- A message from a human client (``html_client``) is always answered and
  resets every agent-to-agent counter, so the mentor can always re-engage.
- A message from an agent or manager is answered while that sender has
  fewer than ``max_agent_turns`` replies in the current window. When the
  cap is reached, the window closes and reopens ``reopen_after`` seconds
  later with a fresh allowance. Each conversation partner therefore gets
  at most ``max_agent_turns`` replies per ``reopen_after`` seconds.
- Any other sender kind is refused.

This module has no network or disk I/O. The clock is injectable so the
timing rules can be tested without waiting.
"""

from __future__ import annotations

import time
from collections.abc import Callable

DEFAULT_MAX_AGENT_TURNS = 10
DEFAULT_REOPEN_AFTER_SECONDS = 300.0
HUMAN_KIND = "html_client"
AGENT_KINDS = frozenset({"agent", "manager"})


class DialogueGuard:
    def __init__(
        self,
        max_agent_turns: int = DEFAULT_MAX_AGENT_TURNS,
        reopen_after: float = DEFAULT_REOPEN_AFTER_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_agent_turns < 1:
            raise ValueError("max_agent_turns must be at least 1")
        if reopen_after < 0:
            raise ValueError("reopen_after must not be negative")
        self.max_agent_turns = max_agent_turns
        self.reopen_after = reopen_after
        self._clock = clock
        self._turns: dict[str, int] = {}
        self._closed_at: dict[str, float] = {}

    def should_reply(self, sender: str, sender_kind: str) -> bool:
        """Return True if this message should be answered, and count the reply."""
        if sender_kind == HUMAN_KIND:
            self._turns.clear()
            self._closed_at.clear()
            return True
        if sender_kind not in AGENT_KINDS:
            return False

        now = self._clock()
        used = self._turns.get(sender, 0)
        if used >= self.max_agent_turns:
            closed_at = self._closed_at.get(sender, now)
            if now - closed_at < self.reopen_after:
                return False
            # The window has reopened: start a fresh allowance.
            used = 0
            self._closed_at.pop(sender, None)

        used += 1
        self._turns[sender] = used
        if used >= self.max_agent_turns:
            self._closed_at[sender] = now
        return True

    def turns_used(self, sender: str) -> int:
        return self._turns.get(sender, 0)
