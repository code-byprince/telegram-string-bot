"""
Telegram String Session Generator Bot
Main application package
"""

__version__ = "1.0.0"
__author__ = "Your Name"

from app.config import Config
from app.bot import create_app

__all__ = ['Config', 'create_app']
