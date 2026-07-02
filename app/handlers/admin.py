import asyncio
import time

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import RPCError

from app.config import Config
from app.utils.logger import log
from app.utils.stats import stats
from app.utils.state_manager import StateManager


def _is_admin(_, __, message: Message) -> bool:
    return bool(message.from_user) and message.from_user.id in Config.ADMIN_IDS


admin_filter = filters.create(_is_admin)


def _format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def register(app: Client, state_manager: StateManager):
    @app.on_message(filters.command("stats") & filters.private & admin_filter)
    async def stats_handler(client: Client, message: Message):
        total = stats.successful_generations + stats.failed_generations
        success_rate = (
            f"{(stats.successful_generations / total * 100):.1f}%" if total else "N/A"
        )
        active_flows = state_manager.active_count

        text = (
            "📊 **Bot Statistics**\n\n"
            f"👥 Total unique users: `{stats.total_users}`\n"
            f"✅ Successful generations: `{stats.successful_generations}`\n"
            f"❌ Failed generations: `{stats.failed_generations}`\n"
            f"📈 Success rate: `{success_rate}`\n"
            f"🔄 Active generation flows: `{active_flows}`\n"
            f"⏱️ Uptime: `{_format_uptime(stats.uptime_seconds)}`\n\n"
            "_Counters are in-memory only and reset on restart — no persistent "
            "database is used, by design._"
        )
        await message.reply_text(text, quote=True)

    @app.on_message(filters.command("users") & filters.private & admin_filter)
    async def users_handler(client: Client, message: Message):
        await message.reply_text(
            f"👥 Total unique users who have interacted with the bot: "
            f"`{stats.total_users}`\n\n"
            "_Individual user identifiers are not listed here to minimise "
            "exposure of personal data — only the aggregate count is shown._",
            quote=True,
        )

    @app.on_message(filters.command("broadcast") & filters.private & admin_filter)
    async def broadcast_handler(client: Client, message: Message):
        if len(message.command) < 2 and not message.reply_to_message:
            await message.reply_text(
                "Usage: `/broadcast <message>`\n"
                "or reply to a message with `/broadcast` to forward its content.",
                quote=True,
            )
            return

        if message.reply_to_message:
            broadcast_text = message.reply_to_message.text or message.reply_to_message.caption
        else:
            broadcast_text = message.text.split(None, 1)[1]

        if not broadcast_text:
            await message.reply_text("Nothing to broadcast — the message has no text.")
            return

        targets = list(stats.known_users)
        status = await message.reply_text(
            f"📢 Broadcasting to {len(targets)} user(s)..."
        )

        sent, failed = 0, 0
        for user_id in targets:
            try:
                await client.send_message(user_id, broadcast_text)
                sent += 1
            except RPCError:
                failed += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                log.warning(f"Broadcast failed for a user: {type(exc).__name__}")
            await asyncio.sleep(0.05)  # gentle pacing to avoid flood limits

        await status.edit_text(
            f"📢 Broadcast complete.\n✅ Sent: {sent}\n❌ Failed: {failed}"
        )
