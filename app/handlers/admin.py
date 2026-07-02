"""
Admin command handlers
"""

import asyncio
from datetime import datetime, timedelta
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from app.config import Config
from app.utils.logger import setup_logger
from app.handlers.generate import user_sessions

logger = setup_logger(__name__)

# Statistics storage (in-memory, reset on restart)
stats = {
    "total_users": set(),
    "successful_generations": 0,
    "failed_generations": 0,
    "start_time": datetime.now(),
    "total_attempts": 0
}


async def stats_command(client, message: Message):
    """Handle /stats command"""
    user_id = message.from_user.id
    
    if not Config.is_admin(user_id):
        await message.reply_text("⛔ You are not authorized to use this command.")
        return
    
    # Calculate uptime
    uptime = datetime.now() - stats["start_time"]
    uptime_str = str(uptime).split('.')[0]  # Remove microseconds
    
    # Get active users
    active_users = len(user_sessions)
    
    stats_message = (
        f"<b>📊 Bot Statistics</b>\n\n"
        f"<b>📈 Total Users:</b> {len(stats['total_users'])}\n"
        f"<b>👤 Active Users:</b> {active_users}\n"
        f"<b>✅ Successful Generations:</b> {stats['successful_generations']}\n"
        f"<b>❌ Failed Generations:</b> {stats['failed_generations']}\n"
        f"<b>🔄 Total Attempts:</b> {stats['total_attempts']}\n"
        f"<b>⏱️ Uptime:</b> {uptime_str}\n"
        f"<b>⚙️ Admins:</b> {len(Config.ADMIN_IDS)}\n\n"
        f"<i>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
    )
    
    await message.reply_text(stats_message)
    logger.info(f"Stats command executed by admin: {user_id}")


async def users_command(client, message: Message):
    """Handle /users command"""
    user_id = message.from_user.id
    
    if not Config.is_admin(user_id):
        await message.reply_text("⛔ You are not authorized to use this command.")
        return
    
    users = list(stats["total_users"])
    
    if not users:
        await message.reply_text("ℹ️ No users have used the bot yet.")
        return
    
    # Create a formatted list
    user_list = "📊 <b>User List</b>\n\n"
    
    # Show first 50 users
    for i, user_id in enumerate(users[:50], 1):
        try:
            user = await client.get_users(user_id)
            username = f"@{user.username}" if user.username else "No username"
            name = user.first_name or "Unknown"
            user_list += f"{i}. {name} ({username}) - ID: {user_id}\n"
        except:
            user_list += f"{i}. User ID: {user_id}\n"
    
    if len(users) > 50:
        user_list += f"\n<i>... and {len(users) - 50} more users</i>"
    
    user_list += f"\n\n<b>Total Users:</b> {len(users)}"
    
    # Split if message is too long
    if len(user_list) > 4000:
        parts = [user_list[i:i+4000] for i in range(0, len(user_list), 4000)]
        for part in parts:
            await message.reply_text(part)
    else:
        await message.reply_text(user_list)
    
    logger.info(f"Users command executed by admin: {user_id}")


async def broadcast_command(client, message: Message):
    """Handle /broadcast command"""
    user_id = message.from_user.id
    
    if not Config.is_admin(user_id):
        await message.reply_text("⛔ You are not authorized to use this command.")
        return
    
    # Check if there's a broadcast message
    text = message.text.split("/broadcast", 1)
    if len(text) < 2 or not text[1].strip():
        await message.reply_text(
            "ℹ️ <b>Usage:</b> /broadcast [message]\n\n"
            "Send a message to all bot users.\n\n"
            "<b>Example:</b>\n"
            "/broadcast Hello everyone! The bot is now back online."
        )
        return
    
    broadcast_message = text[1].strip()
    users = list(stats["total_users"])
    
    if not users:
        await message.reply_text("ℹ️ No users to broadcast to.")
        return
    
    # Send confirmation
    confirm_msg = await message.reply_text(
        f"⏳ <b>Broadcasting...</b>\n\n"
        f"Sending message to {len(users)} users.\n"
        f"Please wait..."
    )
    
    success_count = 0
    failed_count = 0
    
    # Send to all users
    for user_id in users:
        try:
            await client.send_message(
                user_id,
                f"<b>📢 Announcement</b>\n\n{broadcast_message}\n\n"
                f"<i>This is a broadcast message from the bot administrator.</i>"
            )
            success_count += 1
            await asyncio.sleep(0.5)  # Avoid flood wait
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to send broadcast to user {user_id}: {e}")
    
    # Update confirmation
    await confirm_msg.edit_text(
        f"✅ <b>Broadcast Completed</b>\n\n"
        f"✅ Successfully sent to: {success_count} users\n"
        f"❌ Failed to send to: {failed_count} users\n"
        f"📊 Total users: {len(users)}"
    )
    
    logger.info(f"Broadcast completed by admin: {user_id}. Success: {success_count}, Failed: {failed_count}")
