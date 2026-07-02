from pyrogram import Client, filters
from pyrogram.types import Message

from app.config import Config
from app.utils.stats import stats

WELCOME_MESSAGE = """
👋 **Welcome to {bot_name}!**

I generate a **Pyrogram string session** for your own Telegram account, safely and privately.

🔐 **How it works**
1️⃣ Send /generate to begin
2️⃣ Provide your **API_ID** and **API_HASH** (from my.telegram.org)
3️⃣ Provide your **phone number**
4️⃣ Enter the **login code** Telegram sends you
5️⃣ Enter your **2-Step Verification password**, if enabled

✅ Your session string is sent **only to you**, in this private chat.
🚫 I do **not** store your phone number, OTP, password, or session anywhere — everything is wiped from memory the moment the process ends.

⚠️ **Never share your string session with anyone.** It grants full access to your Telegram account, just like your password.

Type /generate to start, or /cancel to stop an ongoing process at any time.
"""

HELP_MESSAGE = """
**Available commands**

/start – show the welcome message
/generate – start generating your Pyrogram string session
/cancel – cancel an in-progress generation
/help – show this message

Need your API_ID / API_HASH? Get them from **my.telegram.org → API Development Tools**.
"""


def register(app: Client):
    @app.on_message(filters.command("start") & filters.private)
    async def start_handler(client: Client, message: Message):
        stats.register_user(message.from_user.id)
        await message.reply_text(
            WELCOME_MESSAGE.format(bot_name=Config.BOT_NAME),
            quote=True,
        )

    @app.on_message(filters.command("help") & filters.private)
    async def help_handler(client: Client, message: Message):
        stats.register_user(message.from_user.id)
        await message.reply_text(HELP_MESSAGE, quote=True)
