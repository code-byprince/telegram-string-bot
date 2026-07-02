"""
User state models
"""

from enum import Enum
from typing import Optional, Any
from dataclasses import dataclass, field


class UserState(Enum):
    """User states for session generation"""
    INIT = "init"
    AWAITING_API_ID = "awaiting_api_id"
    AWAITING_API_HASH = "awaiting_api_hash"
    AWAITING_PHONE = "awaiting_phone"
    AWAITING_OTP = "awaiting_otp"
    AWAITING_2FA = "awaiting_2fa"
    COMPLETE = "complete"


class UserStep(Enum):
    """Steps in the generation process"""
    INIT = 0
    AWAITING_API_ID = 1
    AWAITING_API_HASH = 2
    AWAITING_PHONE = 3
    AWAITING_OTP = 4
    AWAITING_2FA = 5
    COMPLETE = 6


@dataclass
class SessionData:
    """Session data container"""
    api_id: Optional[int] = None
    api_hash: Optional[str] = None
    phone: Optional[str] = None
    phone_code_hash: Optional[str] = None
    temp_client: Optional[Any] = None
    retry_count: int = 0
    
    def clear(self):
        """Clear all sensitive data"""
        self.api_id = None
        self.api_hash = None
        self.phone = None
        self.phone_code_hash = None
        if self.temp_client:
            try:
                # Stop client if it exists
                import asyncio
                asyncio.create_task(self.temp_client.stop())
            except:
                pass
        self.temp_client = None
        self.retry_count = 0
