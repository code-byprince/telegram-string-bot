"""
Configuration management for the bot
"""

import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Bot configuration from environment variables"""
    
    # Telegram Bot Configuration
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is required")
    
    # Admin Configuration
    ADMIN_IDS = [
        int(admin_id.strip()) 
        for admin_id in os.getenv("ADMIN_IDS", "").split(",") 
        if admin_id.strip()
    ]
    
    # Rate Limiting
    RATE_LIMIT = int(os.getenv("RATE_LIMIT", "3"))
    RATE_LIMIT_PERIOD = int(os.getenv("RATE_LIMIT_PERIOD", "300"))  # 5 minutes
    
    # Timeout Settings
    SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "300"))  # 5 minutes
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Flask Health Check
    PORT = int(os.getenv("PORT", "5000"))
    HOST = os.getenv("HOST", "0.0.0.0")
    
    # API Configuration
    API_ID = os.getenv("API_ID")
    API_HASH = os.getenv("API_HASH")
    
    @classmethod
    def is_admin(cls, user_id: int) -> bool:
        """Check if a user is an admin"""
        return user_id in cls.ADMIN_IDS
    
    @classmethod
    def get_config_dict(cls) -> dict:
        """Get all configuration as a dictionary (hiding sensitive data)"""
        return {
            "BOT_TOKEN": "***" if cls.BOT_TOKEN else None,
            "ADMIN_IDS": cls.ADMIN_IDS,
            "RATE_LIMIT": cls.RATE_LIMIT,
            "RATE_LIMIT_PERIOD": cls.RATE_LIMIT_PERIOD,
            "SESSION_TIMEOUT": cls.SESSION_TIMEOUT,
            "LOG_LEVEL": cls.LOG_LEVEL,
            "PORT": cls.PORT,
            "HOST": cls.HOST,
        }
