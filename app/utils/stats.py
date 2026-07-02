"""
In-memory analytics.

Only non-sensitive bookkeeping is kept: which user IDs have interacted with
the bot, and counters for successful/failed session generations. Nothing
here ever touches phone numbers, OTPs, passwords, or session strings.

Counters reset on process restart by design -- this bot deliberately avoids
any persistent database per the security requirements.
"""

import time
from dataclasses import dataclass, field


@dataclass
class Stats:
    known_users: set[int] = field(default_factory=set)
    successful_generations: int = 0
    failed_generations: int = 0
    started_at: float = field(default_factory=time.time)

    def register_user(self, user_id: int) -> None:
        self.known_users.add(user_id)

    def record_success(self) -> None:
        self.successful_generations += 1

    def record_failure(self) -> None:
        self.failed_generations += 1

    @property
    def total_users(self) -> int:
        return len(self.known_users)

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self.started_at


stats = Stats()
