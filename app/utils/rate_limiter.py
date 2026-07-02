"""
Lightweight in-memory rate limiting.

Two independent limits are tracked per user:
  * a short cool-down between any two commands/messages (anti-spam)
  * a longer cool-down between successive session-generation attempts
    (anti-abuse of Telegram's login-code endpoint, which itself is
    rate-limited server-side via FloodWait)

This is intentionally simple (dict + timestamps) since the bot is expected
to run as a single process. No external cache/database is required.
"""

import time
from threading import Lock


class RateLimiter:
    def __init__(self, command_cooldown: float, generation_cooldown: float):
        self.command_cooldown = command_cooldown
        self.generation_cooldown = generation_cooldown
        self._last_command: dict[int, float] = {}
        self._last_generation: dict[int, float] = {}
        self._lock = Lock()

    def allow_command(self, user_id: int) -> bool:
        with self._lock:
            now = time.monotonic()
            last = self._last_command.get(user_id, 0)
            if now - last < self.command_cooldown:
                return False
            self._last_command[user_id] = now
            return True

    def allow_generation(self, user_id: int) -> tuple[bool, float]:
        """Returns (allowed, seconds_remaining_if_not_allowed)."""
        with self._lock:
            now = time.monotonic()
            last = self._last_generation.get(user_id, 0)
            elapsed = now - last
            if elapsed < self.generation_cooldown:
                return False, round(self.generation_cooldown - elapsed, 1)
            self._last_generation[user_id] = now
            return True, 0.0
