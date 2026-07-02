"""
Cancel command handler
"""

from pyrogram.types import Message
from app.handlers.generate import _cleanup_user_session
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


async def cancel_command(client, message: Message):
    """Handle /cancel command"""
    user_id = message.from_user.id
    
    if user_id in user_sessions:
        _cleanup_user_session(user_id)
        await message.reply_text(
            "✅ <b>Process Cancelled</b>\n\n"
            "The session generation process has been cancelled.\n"
            "All your data has been cleared.\n\n"
            "You can start a new session anytime using /generate."
        )
        logger.info(f"User {user_id} cancelled the process")
    else:
        await message.reply_text(
            "ℹ️ <b>No Active Process</b>\n\n"
            "You don't have any active session generation process to cancel.\n"
            "Use /generate to start a new session."
        )
