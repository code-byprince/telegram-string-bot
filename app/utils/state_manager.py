"""
In-memory finite-state-machine for the /generate conversation.

Design goals:
  * Nothing is ever written to disk or a database.
  * Only one active generation flow per user at a time.
  * Sensitive fields (api_hash, phone, otp digits, password, the Pyrogram
    client holding the in-memory Telegram session) are explicitly wiped
    the moment they are no longer needed, and always on cleanup.
  * Inactive flows are auto-cancelled after a configurable timeout.
"""

import asyncio
import enum
import time
from dataclasses import dataclass, field
from typing import Optional

from app.utils.logger import log


class Step(enum.Enum):
    ASK_API_ID = "ASK_API_ID"
    ASK_API_HASH = "ASK_API_HASH"
    ASK_PHONE = "ASK_PHONE"
    ASK_OTP = "ASK_OTP"
    ASK_PASSWORD = "ASK_PASSWORD"


@dataclass
class UserState:
    user_id: int
    step: Step
    created_at: float = field(default_factory=time.monotonic)
    updated_at: float = field(default_factory=time.monotonic)

    api_id: Optional[int] = None
    api_hash: Optional[str] = None
    phone: Optional[str] = None
    phone_code_hash: Optional[str] = None

    client: Optional[object] = None  # pyrogram.Client, in-memory session

    otp_attempts: int = 0
    password_attempts: int = 0

    timeout_task: Optional[asyncio.Task] = None

    def touch(self) -> None:
        self.updated_at = time.monotonic()

    def wipe_secrets(self) -> None:
        """Explicitly clear sensitive attributes from memory."""
        self.api_hash = None
        self.phone = None
        self.phone_code_hash = None
        self.client = None


class StateManager:
    def __init__(self, timeout_seconds: int):
        self.timeout_seconds = timeout_seconds
        self._states: dict[int, UserState] = {}
        self._lock = asyncio.Lock()

    def has_active(self, user_id: int) -> bool:
        return user_id in self._states

    @property
    def active_count(self) -> int:
        return len(self._states)

    def get(self, user_id: int) -> Optional[UserState]:
        return self._states.get(user_id)

    async def start(self, user_id: int, on_timeout) -> UserState:
        async with self._lock:
            await self._clear_locked(user_id)
            state = UserState(user_id=user_id, step=Step.ASK_API_ID)
            state.timeout_task = asyncio.create_task(
                self._watch_timeout(user_id, on_timeout)
            )
            self._states[user_id] = state
            return state

    async def advance(self, user_id: int, step: Step) -> None:
        state = self._states.get(user_id)
        if state:
            state.step = step
            state.touch()

    async def clear(self, user_id: int) -> None:
        async with self._lock:
            await self._clear_locked(user_id)

    async def _clear_locked(self, user_id: int) -> None:
        state = self._states.pop(user_id, None)
        if state is None:
            return

        if state.timeout_task and not state.timeout_task.done():
            state.timeout_task.cancel()

        client = state.client
        state.wipe_secrets()

        if client is not None:
            try:
                if client.is_connected:
                    await client.disconnect()
            except Exception as exc:  # noqa: BLE001
                log.warning(f"Error disconnecting temp client during cleanup: {exc}")

    async def _watch_timeout(self, user_id: int, on_timeout) -> None:
        try:
            await asyncio.sleep(self.timeout_seconds)
            state = self._states.get(user_id)
            if state is None:
                return
            log.info(f"Session generation timed out for user_id={user_id}")
            await self.clear(user_id)
            await on_timeout(user_id)
        except asyncio.CancelledError:
            pass
