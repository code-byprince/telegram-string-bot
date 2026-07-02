"""
Central configuration module.

All runtime configuration is loaded from environment variables (via a .env
file locally, or Render's environment variable dashboard in production).
Nothing sensitive is hard-coded here.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids(raw: str) -> list[int]:
    ids = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids


class Config:
    # --- Bot's own Telegram credentials (used to run the bot itself) ---
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    API_ID: int = int(os.getenv("API_ID", "0") or "0")
    API_HASH: str = os.getenv("API_HASH", "")

    # --- Admin access ---
    ADMIN_IDS: list[int] = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))

    # --- Web server (Render health check) ---
    PORT: int = int(os.getenv("PORT", "8080"))

    # --- Behaviour tuning ---
    SESSION_TIMEOUT_SECONDS: int = int(os.getenv("SESSION_TIMEOUT_SECONDS", "300"))
    RATE_LIMIT_SECONDS: int = int(os.getenv("RATE_LIMIT_SECONDS", "60"))
    COMMAND_RATE_LIMIT_SECONDS: int = int(os.getenv("COMMAND_RATE_LIMIT_SECONDS", "2"))
    MAX_OTP_ATTEMPTS: int = int(os.getenv("MAX_OTP_ATTEMPTS", "3"))
    MAX_PASSWORD_ATTEMPTS: int = int(os.getenv("MAX_PASSWORD_ATTEMPTS", "3"))

    # --- Logging ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # --- Misc ---
    BOT_NAME: str = os.getenv("BOT_NAME", "String Session Generator")
    SUPPORT_USERNAME: str = os.getenv("SUPPORT_USERNAME", "")

    @classmethod
    def validate(cls) -> None:
        """Raise a clear error early if required configuration is missing."""
        missing = []
        if not cls.BOT_TOKEN:
            missing.append("BOT_TOKEN")
        if not cls.API_ID:
            missing.append("API_ID")
        if not cls.API_HASH:
            missing.append("API_HASH")
        if not cls.ADMIN_IDS:
            missing.append("ADMIN_IDS")

        if missing:
            raise RuntimeError(
                "Missing required environment variable(s): "
                + ", ".join(missing)
                + ". Check your .env file (see .env.example)."
            )
