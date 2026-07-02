"""
The /generate conversation flow.

State machine steps:
    ASK_API_ID -> ASK_API_HASH -> ASK_PHONE -> ASK_OTP -> [ASK_PASSWORD] -> done

A temporary, in-memory-only Pyrogram Client (the user's own API_ID/API_HASH)
is used to request a login code and sign in. Once a session string has been
exported it is sent to the requesting user and the temporary client, plus
every other sensitive field, is wiped from memory immediately.
"""

import asyncio

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import (
    ApiIdInvalid,
    PhoneNumberInvalid,
    PhoneNumberBanned,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    PasswordHashInvalid,
    FloodWait,
    RPCError,
)

from app.config import Config
from app.utils.logger import log
from app.utils.stats import stats
from app.utils.rate_limiter import RateLimiter
from app.utils.state_manager import StateManager, Step
from app.utils.validators import (
    validate_api_id,
    validate_api_hash,
    validate_phone,
    validate_otp,
    validate_password,
)

state_manager = StateManager(timeout_seconds=Config.SESSION_TIMEOUT_SECONDS)
rate_limiter = RateLimiter(
    command_cooldown=Config.COMMAND_RATE_LIMIT_SECONDS,
    generation_cooldown=Config.RATE_LIMIT_SECONDS,
)


def _in_flow(_, __, message: Message) -> bool:
    if not message.from_user:
        return False
    return state_manager.has_active(message.from_user.id)


in_flow_filter = filters.create(_in_flow)


def register(app: Client):
    async def notify_timeout(user_id: int):
        try:
            await app.send_message(
                user_id,
                "⌛ Your session generation request timed out due to inactivity. "
                "Send /generate to start again.",
            )
        except Exception as exc:  # noqa: BLE001
            log.warning(f"Could not notify user about timeout: {exc}")

    @app.on_message(filters.command("generate") & filters.private)
    async def generate_start(client: Client, message: Message):
        user_id = message.from_user.id
        stats.register_user(user_id)

        if not rate_limiter.allow_command(user_id):
            return

        if state_manager.has_active(user_id):
            await message.reply_text(
                "⚠️ You already have a session generation in progress.\n"
                "Send /cancel to stop it before starting a new one.",
                quote=True,
            )
            return

        allowed, wait_seconds = rate_limiter.allow_generation(user_id)
        if not allowed:
            await message.reply_text(
                f"🚦 Please wait {wait_seconds}s before starting another "
                "generation attempt. This limit protects your account from "
                "Telegram's own anti-abuse restrictions.",
                quote=True,
            )
            return

        await state_manager.start(user_id, notify_timeout)
        await message.reply_text(
            "🔢 **Step 1/4 — API_ID**\n\n"
            "Please send your **API_ID**.\n"
            "You can get this from https://my.telegram.org → *API Development Tools*.\n\n"
            "Send /cancel anytime to stop.",
            quote=True,
        )

    @app.on_message(filters.command("cancel") & filters.private)
    async def cancel_flow(client: Client, message: Message):
        user_id = message.from_user.id
        if not state_manager.has_active(user_id):
            await message.reply_text("Nothing to cancel — no active generation in progress.")
            return
        await state_manager.clear(user_id)
        await message.reply_text("❌ Cancelled. All temporary data for this session has been wiped.")

    @app.on_message(filters.private & filters.text & in_flow_filter)
    async def flow_step(client: Client, message: Message):
        user_id = message.from_user.id
        state = state_manager.get(user_id)
        if state is None:
            return

        text = message.text.strip()
        state.touch()

        if text.startswith("/"):
            # Let dedicated command handlers deal with commands like /cancel.
            return

        if state.step == Step.ASK_API_ID:
            await _handle_api_id(message, state)
        elif state.step == Step.ASK_API_HASH:
            await _handle_api_hash(message, state)
        elif state.step == Step.ASK_PHONE:
            await _handle_phone(message, state)
        elif state.step == Step.ASK_OTP:
            await _handle_otp(message, state)
        elif state.step == Step.ASK_PASSWORD:
            await _handle_password(message, state)


async def _handle_api_id(message: Message, state):
    ok, value = validate_api_id(message.text)
    if not ok:
        await message.reply_text(f"❌ {value}")
        return
    state.api_id = int(value)
    await state_manager.advance(state.user_id, Step.ASK_API_HASH)
    await message.reply_text(
        "🔑 **Step 2/4 — API_HASH**\n\nNow send your **API_HASH** (32-character string)."
    )


async def _handle_api_hash(message: Message, state):
    ok, value = validate_api_hash(message.text)
    if not ok:
        await message.reply_text(f"❌ {value}")
        return
    state.api_hash = value
    await state_manager.advance(state.user_id, Step.ASK_PHONE)
    await message.reply_text(
        "📱 **Step 3/4 — Phone Number**\n\n"
        "Send your phone number in international format, e.g. `+919876543210`."
    )


async def _handle_phone(message: Message, state):
    ok, value = validate_phone(message.text)
    if not ok:
        await message.reply_text(f"❌ {value}")
        return

    status_msg = await message.reply_text("⏳ Requesting login code from Telegram...")

    client = Client(
        name=f"session_gen_{state.user_id}",
        api_id=state.api_id,
        api_hash=state.api_hash,
        in_memory=True,
    )

    try:
        await client.connect()
        sent_code = await client.send_code(value)
    except ApiIdInvalid:
        await status_msg.edit_text(
            "❌ Your API_ID / API_HASH pair is invalid. Send /generate to start over."
        )
        await _cleanup_failed(state)
        return
    except PhoneNumberInvalid:
        await status_msg.edit_text(
            "❌ Invalid phone number. Send /generate to start over with a valid number."
        )
        await _cleanup_failed(state)
        return
    except PhoneNumberBanned:
        await status_msg.edit_text(
            "❌ This phone number is banned from Telegram. I can't generate a session for it."
        )
        await _cleanup_failed(state)
        return
    except FloodWait as e:
        await status_msg.edit_text(
            f"⏱️ Telegram is rate-limiting this action. Please try again in {e.value} seconds."
        )
        await _cleanup_failed(state)
        return
    except RPCError as e:
        log.warning(f"send_code RPCError (type={type(e).__name__})")
        await status_msg.edit_text(
            "❌ Telegram rejected the request. Please double-check your details and try /generate again."
        )
        await _cleanup_failed(state)
        return

    state.phone = value
    state.phone_code_hash = sent_code.phone_code_hash
    state.client = client
    await state_manager.advance(state.user_id, Step.ASK_OTP)

    await status_msg.edit_text(
        "✅ Code sent!\n\n"
        "🔐 **Step 4/4 — Login Code**\n\n"
        "Please send the login code Telegram just sent you.\n"
        "_Tip: if the code looks like `1-2-3-4-5`, just send the digits: `12345`._"
    )


async def _handle_otp(message: Message, state):
    ok, value = validate_otp(message.text)
    if not ok:
        await message.reply_text(f"❌ {value}")
        return

    client = state.client
    if client is None:
        await message.reply_text("Something went wrong. Send /generate to start over.")
        await state_manager.clear(state.user_id)
        return

    status_msg = await message.reply_text("⏳ Verifying code...")

    try:
        await client.sign_in(state.phone, state.phone_code_hash, value)
    except SessionPasswordNeeded:
        await state_manager.advance(state.user_id, Step.ASK_PASSWORD)
        await status_msg.edit_text(
            "🔒 Two-Step Verification is enabled on this account.\n\n"
            "Please send your **2-Step Verification password**."
        )
        return
    except PhoneCodeInvalid:
        state.otp_attempts += 1
        if state.otp_attempts >= Config.MAX_OTP_ATTEMPTS:
            await status_msg.edit_text(
                "❌ Too many invalid attempts. Send /generate to start over."
            )
            await _cleanup_failed(state)
            return
        await status_msg.edit_text(
            f"❌ Invalid code. Please try again "
            f"({state.otp_attempts}/{Config.MAX_OTP_ATTEMPTS})."
        )
        return
    except PhoneCodeExpired:
        await status_msg.edit_text(
            "❌ This code has expired. Send /generate to start over."
        )
        await _cleanup_failed(state)
        return
    except FloodWait as e:
        await status_msg.edit_text(
            f"⏱️ Telegram is rate-limiting this action. Please try again in {e.value} seconds."
        )
        await _cleanup_failed(state)
        return
    except RPCError as e:
        log.warning(f"sign_in RPCError (type={type(e).__name__})")
        await status_msg.edit_text(
            "❌ Sign-in failed. Send /generate to start over."
        )
        await _cleanup_failed(state)
        return

    await _finish_success(status_msg, state)


async def _handle_password(message: Message, state):
    ok, value = validate_password(message.text)
    if not ok:
        await message.reply_text(f"❌ {value}")
        return

    client = state.client
    if client is None:
        await message.reply_text("Something went wrong. Send /generate to start over.")
        await state_manager.clear(state.user_id)
        return

    status_msg = await message.reply_text("⏳ Verifying password...")

    try:
        await client.check_password(value)
    except PasswordHashInvalid:
        state.password_attempts += 1
        if state.password_attempts >= Config.MAX_PASSWORD_ATTEMPTS:
            await status_msg.edit_text(
                "❌ Too many incorrect attempts. Send /generate to start over."
            )
            await _cleanup_failed(state)
            return
        await status_msg.edit_text(
            f"❌ Incorrect password. Please try again "
            f"({state.password_attempts}/{Config.MAX_PASSWORD_ATTEMPTS})."
        )
        return
    except FloodWait as e:
        await status_msg.edit_text(
            f"⏱️ Telegram is rate-limiting this action. Please try again in {e.value} seconds."
        )
        await _cleanup_failed(state)
        return
    except RPCError as e:
        log.warning(f"check_password RPCError (type={type(e).__name__})")
        await status_msg.edit_text("❌ Verification failed. Send /generate to start over.")
        await _cleanup_failed(state)
        return

    await _finish_success(status_msg, state)


async def _finish_success(status_msg: Message, state):
    client = state.client
    try:
        session_string = await client.export_session_string()
    except Exception as exc:  # noqa: BLE001
        log.error(f"Failed to export session string: {type(exc).__name__}")
        await status_msg.edit_text(
            "❌ Something went wrong while generating your session. Please try /generate again."
        )
        stats.record_failure()
        await _cleanup_failed(state)
        return

    try:
        await status_msg.edit_text(
            "✅ **Success!** Your string session is below.\n\n"
            "⚠️ **Keep it private** — anyone with this string has full access "
            "to your Telegram account. Never share it or paste it into an "
            "untrusted bot or website."
        )
        await status_msg.reply_text(f"`{session_string}`")
    finally:
        # Wipe the local variable regardless of what happens above.
        session_string = None  # noqa: F841
        del session_string

    stats.record_success()
    log.info(f"Session string generated successfully for user_id={state.user_id}")

    user_id = state.user_id
    await state_manager.clear(user_id)


async def _cleanup_failed(state):
    stats.record_failure()
    await state_manager.clear(state.user_id)
