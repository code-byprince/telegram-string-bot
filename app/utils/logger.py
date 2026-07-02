"""
Structured logging setup.

IMPORTANT: Handlers must never pass phone numbers, OTP codes, 2FA passwords,
API_HASH values, or generated session strings to the logger. This module
adds a safety-net filter that redacts a few obviously sensitive patterns if
they ever slip into a log message, but the primary defense is discipline in
the calling code (never log those values in the first place).
"""

import logging
import re
import sys

_SENSITIVE_PATTERNS = [
    re.compile(r"(session string[:\s]*)\S+", re.IGNORECASE),
    re.compile(r"\+?\d{8,15}"),  # phone-number-like sequences
]


class RedactSensitiveFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True

        redacted = msg
        for pattern in _SENSITIVE_PATTERNS:
            redacted = pattern.sub("[REDACTED]", redacted)

        if redacted != msg:
            record.msg = redacted
            record.args = ()

        return True


def setup_logger(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("session_bot")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    handler.addFilter(RedactSensitiveFilter())
    logger.addHandler(handler)

    # Quiet down noisy third-party loggers
    logging.getLogger("pyrogram").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    return logger


log = setup_logger()
