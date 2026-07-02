"""
Start command handler
"""

from pyrogram.types import Message
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


async def start_command(client, message: Message):
    """Handle /start command"""
    user = message.from_user
    
    logger.info(f"Start command from user: {user.id} (@{user.username or 'unknown'})")
    
    welcome_message = (
        f"<b>🌟 Welcome {user.mention()}!</b>\n\n"
        "I am a <b>Telegram String Session Generator</b> bot.\n"
        "I can help you generate Pyrogram string sessions securely.\n\n"
        "<b>📌 How to use:</b>\n"
        "1️⃣ Use /generate to start the session generation\n"
        "2️⃣ Provide your API_ID and API_HASH\n"
        "3️⃣ Enter your phone number\n"
        "4️⃣ Enter the OTP code you receive\n"
        "5️⃣ Enter your 2FA password (if enabled)\n\n"
        "<b>🔐 Security:</b>\n"
        "• Your credentials are never stored\n"
        "• Sessions are generated securely\n"
        "• All data is cleared after completion\n\n"
        "<b>⚠️ Commands:</b>\n"
        "/generate - Start string session generation\n"
        "/cancel - Cancel current operation\n"
        "/stats - Bot statistics (Admin only)\n"
        "/users - List users (Admin only)\n"
        "/broadcast - Send message to all users (Admin only)\n\n"
        "<i>💡 Tip: Use /cancel at any time to stop the process</i>"
    )
    
    await message.reply_text(welcome_message)
