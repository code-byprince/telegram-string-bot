"""
Generate command and conversation handlers
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from pyrogram import Client, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    FloodWait,
    ApiIdInvalid,
    ApiIdPublishedFlood,
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    PasswordHashInvalid,
    SessionPasswordNeeded,
    BadRequest
)
from app.config import Config
from app.utils.state_manager import StateManager
from app.utils.validators import validate_api_id, validate_api_hash, validate_phone
from app.utils.logger import setup_logger
from app.models.user_state import UserState, UserStep, SessionData

logger = setup_logger(__name__)

# Rate limiting storage
rate_limits: Dict[int, Dict[str, Any]] = {}
user_sessions: Dict[int, Dict[str, Any]] = {}


async def generate_command(client, message: Message):
    """Handle /generate command"""
    user_id = message.from_user.id
    
    # Check rate limiting
    if not _check_rate_limit(user_id):
        await message.reply_text(
            "⚠️ <b>Rate Limit Exceeded</b>\n\n"
            f"You have reached the maximum number of attempts ({Config.RATE_LIMIT}) "
            f"in the last {Config.RATE_LIMIT_PERIOD // 60} minutes.\n\n"
            "Please try again later."
        )
        return
    
    # Check if user already has an active session
    if user_id in user_sessions:
        await message.reply_text(
            "⚠️ <b>Active Session in Progress</b>\n\n"
            "You already have an active session generation process.\n"
            "Please complete or cancel it first.\n\n"
            "Use /cancel to cancel the current session."
        )
        return
    
    # Initialize session
    user_sessions[user_id] = {
        "state": UserState.INIT,
        "data": SessionData(),
        "last_active": datetime.now(),
        "step": UserStep.INIT
    }
    
    # Send initial message
    await message.reply_text(
        "<b>🔐 String Session Generator</b>\n\n"
        "To generate your Pyrogram string session, I need some information.\n\n"
        "Please follow the steps below:\n\n"
        "<b>Step 1:</b> Enter your <b>API_ID</b>\n"
        "<i>You can get this from https://my.telegram.org</i>\n\n"
        "Type <b>/cancel</b> at any time to cancel the process.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_generation")]
        ])
    )
    
    # Update state
    user_sessions[user_id]["state"] = UserState.AWAITING_API_ID
    user_sessions[user_id]["step"] = UserStep.AWAITING_API_ID
    
    logger.info(f"Started session generation for user: {user_id}")


async def text_message_handler(client, message: Message):
    """Handle text messages during conversation"""
    user_id = message.from_user.id
    
    # Check if user has an active session
    if user_id not in user_sessions:
        # Check if user is trying to provide input without starting
        if message.text and not message.text.startswith('/'):
            await message.reply_text(
                "⚠️ <b>No Active Session</b>\n\n"
                "Please start a new session using /generate command."
            )
        return
    
    # Update last active time
    user_sessions[user_id]["last_active"] = datetime.now()
    
    session = user_sessions[user_id]
    current_state = session["state"]
    data = session["data"]
    
    try:
        # Handle input based on current state
        if current_state == UserState.AWAITING_API_ID:
            await _handle_api_id(client, message, user_id, session, data)
        elif current_state == UserState.AWAITING_API_HASH:
            await _handle_api_hash(client, message, user_id, session, data)
        elif current_state == UserState.AWAITING_PHONE:
            await _handle_phone(client, message, user_id, session, data)
        elif current_state == UserState.AWAITING_OTP:
            await _handle_otp(client, message, user_id, session, data)
        elif current_state == UserState.AWAITING_2FA:
            await _handle_2fa(client, message, user_id, session, data)
        else:
            await message.reply_text(
                "⚠️ Invalid state. Please use /cancel and try again."
            )
    except FloodWait as e:
        await message.reply_text(
            f"⏳ <b>Flood Wait</b>\n\n"
            f"Telegram is limiting requests. Please wait {e.value} seconds before trying again."
        )
    except Exception as e:
        logger.error(f"Error in text message handler for user {user_id}: {e}")
        await message.reply_text(
            "❌ <b>An Error Occurred</b>\n\n"
            "Something went wrong. Please use /cancel and try again.\n"
            "If the problem persists, contact an administrator."
        )
        _cleanup_user_session(user_id)


async def callback_handler(client, callback_query: CallbackQuery):
    """Handle callback queries"""
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    if data == "cancel_generation":
        await cancel_generation(client, callback_query)
    elif data == "confirm_cancel":
        await confirm_cancel(client, callback_query)
    elif data == "continue_generation":
        await continue_generation(client, callback_query)
    else:
        await callback_query.answer("Unknown action", show_alert=True)


async def _handle_api_id(client, message: Message, user_id: int, session: Dict, data: SessionData):
    """Handle API_ID input"""
    api_id = message.text.strip()
    
    if not validate_api_id(api_id):
        await message.reply_text(
            "❌ <b>Invalid API_ID</b>\n\n"
            "API_ID must be a valid integer.\n"
            "Please enter a valid API_ID or use /cancel to cancel.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_generation")]
            ])
        )
        return
    
    data.api_id = int(api_id)
    session["state"] = UserState.AWAITING_API_HASH
    session["step"] = UserStep.AWAITING_API_HASH
    
    await message.reply_text(
        "✅ <b>API_ID accepted!</b>\n\n"
        "<b>Step 2:</b> Enter your <b>API_HASH</b>\n"
        "<i>You can get this from https://my.telegram.org</i>\n\n"
        "Type /cancel to cancel.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_generation")]
        ])
    )
    
    logger.info(f"User {user_id} provided API_ID")


async def _handle_api_hash(client, message: Message, user_id: int, session: Dict, data: SessionData):
    """Handle API_HASH input"""
    api_hash = message.text.strip()
    
    if not validate_api_hash(api_hash):
        await message.reply_text(
            "❌ <b>Invalid API_HASH</b>\n\n"
            "API_HASH must be a valid alphanumeric string.\n"
            "Please enter a valid API_HASH or use /cancel to cancel.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_generation")]
            ])
        )
        return
    
    data.api_hash = api_hash
    session["state"] = UserState.AWAITING_PHONE
    session["step"] = UserStep.AWAITING_PHONE
    
    await message.reply_text(
        "✅ <b>API_HASH accepted!</b>\n\n"
        "<b>Step 3:</b> Enter your <b>Phone Number</b>\n"
        "<i>Format: +1234567890 (with country code)</i>\n\n"
        "Type /cancel to cancel.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_generation")]
        ])
    )
    
    logger.info(f"User {user_id} provided API_HASH")


async def _handle_phone(client, message: Message, user_id: int, session: Dict, data: SessionData):
    """Handle phone number input"""
    phone = message.text.strip()
    
    if not validate_phone(phone):
        await message.reply_text(
            "❌ <b>Invalid Phone Number</b>\n\n"
            "Please enter a valid phone number with country code.\n"
            "Format: +1234567890\n\n"
            "Please try again or use /cancel to cancel.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_generation")]
            ])
        )
        return
    
    data.phone = phone
    
    # Send "sending code" message
    status_msg = await message.reply_text(
        "📱 <b>Sending OTP Code</b>\n\n"
        "Please wait while we send the verification code to your Telegram account..."
    )
    
    try:
        # Initialize a temporary client to send code
        temp_client = Client(
            f"temp_{user_id}",
            api_id=data.api_id,
            api_hash=data.api_hash,
            in_memory=True
        )
        
        await temp_client.start()
        
        # Send code
        sent_code = await temp_client.send_code(phone)
        
        data.phone_code_hash = sent_code.phone_code_hash
        session["state"] = UserState.AWAITING_OTP
        session["step"] = UserStep.AWAITING_OTP
        session["temp_client"] = temp_client
        
        await status_msg.edit_text(
            "✅ <b>OTP Code Sent!</b>\n\n"
            "<b>Step 4:</b> Enter the <b>OTP Code</b> you received\n"
            "<i>Format: 12345 (5-6 digits)</i>\n\n"
            "Type /cancel to cancel.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_generation")]
            ])
        )
        
        logger.info(f"OTP code sent to user {user_id}")
        
    except ApiIdInvalid:
        await status_msg.edit_text(
            "❌ <b>Invalid API Credentials</b>\n\n"
            "The API_ID and API_HASH you provided are invalid.\n"
            "Please use /cancel and start over with correct credentials."
        )
        _cleanup_user_session(user_id)
    except ApiIdPublishedFlood:
        await status_msg.edit_text(
            "⚠️ <b>API ID Published</b>\n\n"
            "This API_ID has been published and is not allowed.\n"
            "Please use a different API_ID from https://my.telegram.org"
        )
        _cleanup_user_session(user_id)
    except PhoneNumberInvalid:
        await status_msg.edit_text(
            "❌ <b>Invalid Phone Number</b>\n\n"
            "The phone number you entered is invalid.\n"
            "Please use /cancel and try again with a valid number."
        )
        _cleanup_user_session(user_id)
    except Exception as e:
        logger.error(f"Error sending OTP for user {user_id}: {e}")
        await status_msg.edit_text(
            "❌ <b>Error Sending OTP</b>\n\n"
            "Failed to send OTP. Please use /cancel and try again."
        )
        _cleanup_user_session(user_id)


async def _handle_otp(client, message: Message, user_id: int, session: Dict, data: SessionData):
    """Handle OTP input"""
    otp = message.text.strip()
    
    if not otp.isdigit() or len(otp) not in [5, 6]:
        await message.reply_text(
            "❌ <b>Invalid OTP Format</b>\n\n"
            "OTP must be 5 or 6 digits.\n"
            "Please enter the correct OTP or use /cancel to cancel.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_generation")]
            ])
        )
        return
    
    temp_client = session.get("temp_client")
    if not temp_client:
        await message.reply_text(
            "❌ <b>Session Error</b>\n\n"
            "Client session not found. Please use /cancel and start over."
        )
        _cleanup_user_session(user_id)
        return
    
    try:
        # Try to sign in with OTP
        await message.reply_text(
            "⏳ <b>Verifying OTP...</b>\n\n"
            "Please wait while we verify your code."
        )
        
        try:
            await temp_client.sign_in(
                data.phone,
                data.phone_code_hash,
                otp
            )
            
            # Success! Generate string session
            string_session = await temp_client.export_session_string()
            
            # Send the string session to the user
            await client.send_message(
                user_id,
                f"<b>✅ String Session Generated Successfully!</b>\n\n"
                f"<code>{string_session}</code>\n\n"
                f"<b>⚠️ Important:</b>\n"
                f"• Keep this string session secure\n"
                f"• Never share it with anyone\n"
                f"• Use this with Pyrogram like:\n"
                f"<code>app = Client('session', api_id=YOUR_API_ID, api_hash=YOUR_API_HASH)</code>\n\n"
                f"<b>🔄 Session Details:</b>\n"
                f"• User ID: {temp_client.me.id}\n"
                f"• First Name: {temp_client.me.first_name or 'N/A'}\n"
                f"• Last Name: {temp_client.me.last_name or 'N/A'}\n"
                f"• Username: @{temp_client.me.username or 'N/A'}\n\n"
                f"<i>This message will be deleted after 10 minutes for security.</i>"
            )
            
            # Schedule message deletion after 10 minutes
            asyncio.create_task(_delete_after_delay(client, user_id, 600))
            
            # Log success
            logger.info(f"String session generated successfully for user: {user_id}")
            
            # Cleanup
            await temp_client.stop()
            _cleanup_user_session(user_id)
            
        except PhoneCodeInvalid:
            await message.reply_text(
                "❌ <b>Invalid OTP</b>\n\n"
                "The OTP code you entered is incorrect.\n"
                "Please try again or use /cancel to cancel.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data="cancel_generation")]
                ])
            )
        except PhoneCodeExpired:
            await message.reply_text(
                "❌ <b>OTP Expired</b>\n\n"
                "The OTP code has expired.\n"
                "Please use /cancel and start over to receive a new code."
            )
            _cleanup_user_session(user_id)
        except SessionPasswordNeeded:
            # 2FA is enabled
            session["state"] = UserState.AWAITING_2FA
            session["step"] = UserStep.AWAITING_2FA
            
            await message.reply_text(
                "🔐 <b>Two-Step Verification</b>\n\n"
                "Your account has 2FA enabled.\n"
                "<b>Step 5:</b> Enter your <b>2FA Password</b>\n\n"
                "Type /cancel to cancel.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data="cancel_generation")]
                ])
            )
            
        except PasswordHashInvalid:
            await message.reply_text(
                "❌ <b>Invalid 2FA Password</b>\n\n"
                "The password you entered is incorrect.\n"
                "Please try again or use /cancel to cancel.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data="cancel_generation")]
                ])
            )
        except BadRequest as e:
            if "PASSWORD_HASH_INVALID" in str(e):
                await message.reply_text(
                    "❌ <b>Invalid 2FA Password</b>\n\n"
                    "The password you entered is incorrect.\n"
                    "Please try again or use /cancel to cancel.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_generation")]
                    ])
                )
            else:
                raise
                
    except Exception as e:
        logger.error(f"Error verifying OTP for user {user_id}: {e}")
        await message.reply_text(
            "❌ <b>Error Verifying OTP</b>\n\n"
            "Something went wrong. Please use /cancel and try again."
        )
        _cleanup_user_session(user_id)


async def _handle_2fa(client, message: Message, user_id: int, session: Dict, data: SessionData):
    """Handle 2FA password input"""
    password = message.text.strip()
    
    if not password:
        await message.reply_text(
            "❌ <b>Invalid Password</b>\n\n"
            "Password cannot be empty.\n"
            "Please enter your 2FA password or use /cancel to cancel.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_generation")]
            ])
        )
        return
    
    temp_client = session.get("temp_client")
    if not temp_client:
        await message.reply_text(
            "❌ <b>Session Error</b>\n\n"
            "Client session not found. Please use /cancel and start over."
        )
        _cleanup_user_session(user_id)
        return
    
    try:
        await message.reply_text(
            "⏳ <b>Verifying 2FA Password...</b>\n\n"
            "Please wait while we verify your password."
        )
        
        # Check password
        await temp_client.check_password(password)
        
        # Complete sign in
        await temp_client.sign_in(
            data.phone,
            data.phone_code_hash
        )
        
        # Generate string session
        string_session = await temp_client.export_session_string()
        
        # Send the string session to the user
        await client.send_message(
            user_id,
            f"<b>✅ String Session Generated Successfully!</b>\n\n"
            f"<code>{string_session}</code>\n\n"
            f"<b>⚠️ Important:</b>\n"
            f"• Keep this string session secure\n"
            f"• Never share it with anyone\n"
            f"• Use this with Pyrogram like:\n"
            f"<code>app = Client('session', api_id=YOUR_API_ID, api_hash=YOUR_API_HASH)</code>\n\n"
            f"<b>🔄 Session Details:</b>\n"
            f"• User ID: {temp_client.me.id}\n"
            f"• First Name: {temp_client.me.first_name or 'N/A'}\n"
            f"• Last Name: {temp_client.me.last_name or 'N/A'}\n"
            f"• Username: @{temp_client.me.username or 'N/A'}\n\n"
            f"<i>This message will be deleted after 10 minutes for security.</i>"
        )
        
        # Schedule message deletion after 10 minutes
        asyncio.create_task(_delete_after_delay(client, user_id, 600))
        
        # Log success
        logger.info(f"String session generated successfully with 2FA for user: {user_id}")
        
        # Cleanup
        await temp_client.stop()
        _cleanup_user_session(user_id)
        
    except PasswordHashInvalid:
        await message.reply_text(
            "❌ <b>Invalid 2FA Password</b>\n\n"
            "The password you entered is incorrect.\n"
            "Please try again or use /cancel to cancel.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_generation")]
            ])
        )
    except Exception as e:
        logger.error(f"Error verifying 2FA for user {user_id}: {e}")
        await message.reply_text(
            "❌ <b>Error Verifying 2FA</b>\n\n"
            "Something went wrong. Please use /cancel and try again."
        )
        _cleanup_user_session(user_id)


async def cancel_generation(client, callback_query: CallbackQuery):
    """Cancel generation from callback"""
    user_id = callback_query.from_user.id
    
    if user_id in user_sessions:
        await callback_query.message.edit_text(
            "⚠️ <b>Cancel Generation?</b>\n\n"
            "Are you sure you want to cancel the session generation process?\n"
            "All data will be lost.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Yes, Cancel", callback_data="confirm_cancel"),
                    InlineKeyboardButton("❌ No, Continue", callback_data="continue_generation")
                ]
            ])
        )
        await callback_query.answer()
    else:
        await callback_query.message.edit_text(
            "ℹ️ <b>No Active Session</b>\n\n"
            "You don't have any active session generation process."
        )
        await callback_query.answer()


async def confirm_cancel(client, callback_query: CallbackQuery):
    """Confirm cancellation"""
    user_id = callback_query.from_user.id
    
    _cleanup_user_session(user_id)
    
    await callback_query.message.edit_text(
        "✅ <b>Generation Cancelled</b>\n\n"
        "The session generation process has been cancelled.\n"
        "You can start a new session anytime using /generate."
    )
    await callback_query.answer()


async def continue_generation(client, callback_query: CallbackQuery):
    """Continue generation after cancellation prompt"""
    user_id = callback_query.from_user.id
    
    if user_id in user_sessions:
        session = user_sessions[user_id]
        
        # Resume based on current state
        if session["state"] == UserState.AWAITING_API_ID:
            await callback_query.message.edit_text(
                "<b>🔐 String Session Generator</b>\n\n"
                "<b>Step 1:</b> Enter your <b>API_ID</b>\n"
                "<i>You can get this from https://my.telegram.org</i>\n\n"
                "Type /cancel to cancel."
            )
        elif session["state"] == UserState.AWAITING_API_HASH:
            await callback_query.message.edit_text(
                "<b>🔐 String Session Generator</b>\n\n"
                "<b>Step 2:</b> Enter your <b>API_HASH</b>\n"
                "<i>You can get this from https://my.telegram.org</i>\n\n"
                "Type /cancel to cancel."
            )
        elif session["state"] == UserState.AWAITING_PHONE:
            await callback_query.message.edit_text(
                "<b>🔐 String Session Generator</b>\n\n"
                "<b>Step 3:</b> Enter your <b>Phone Number</b>\n"
                "<i>Format: +1234567890 (with country code)</i>\n\n"
                "Type /cancel to cancel."
            )
        elif session["state"] == UserState.AWAITING_OTP:
            await callback_query.message.edit_text(
                "<b>🔐 String Session Generator</b>\n\n"
                "<b>Step 4:</b> Enter the <b>OTP Code</b> you received\n"
                "<i>Format: 12345 (5-6 digits)</i>\n\n"
                "Type /cancel to cancel."
            )
        elif session["state"] == UserState.AWAITING_2FA:
            await callback_query.message.edit_text(
                "<b>🔐 String Session Generator</b>\n\n"
                "<b>Step 5:</b> Enter your <b>2FA Password</b>\n\n"
                "Type /cancel to cancel."
            )
        else:
            await callback_query.message.edit_text(
                "ℹ️ <b>Session Continued</b>\n\n"
                "Please provide the requested information."
            )
    else:
        await callback_query.message.edit_text(
            "ℹ️ <b>No Active Session</b>\n\n"
            "You don't have any active session generation process."
        )
    
    await callback_query.answer()


def _check_rate_limit(user_id: int) -> bool:
    """Check if user is rate limited"""
    current_time = datetime.now()
    
    if user_id not in rate_limits:
        rate_limits[user_id] = {
            "count": 1,
            "first_request": current_time
        }
        return True
    
    data = rate_limits[user_id]
    elapsed = (current_time - data["first_request"]).total_seconds()
    
    if elapsed > Config.RATE_LIMIT_PERIOD:
        # Reset rate limit
        data["count"] = 1
        data["first_request"] = current_time
        return True
    
    if data["count"] >= Config.RATE_LIMIT:
        return False
    
    data["count"] += 1
    return True


def _cleanup_user_session(user_id: int):
    """Clean up user session data"""
    if user_id in user_sessions:
        session = user_sessions[user_id]
        
        # Stop temp client if exists
        temp_client = session.get("temp_client")
        if temp_client:
            try:
                # Use asyncio.create_task to avoid blocking
                asyncio.create_task(temp_client.stop())
            except:
                pass
        
        # Clear sensitive data
        if "data" in session:
            session["data"].clear()
        
        # Remove session
        del user_sessions[user_id]
        logger.info(f"Cleaned up session for user: {user_id}")
    
    # Clean up rate limit data if exists
    if user_id in rate_limits:
        del rate_limits[user_id]


async def _delete_after_delay(client, chat_id: int, delay: int):
    """Delete message after a delay"""
    await asyncio.sleep(delay)
    try:
        # Get the last message sent to the user (the string session message)
        async for message in client.get_chat_history(chat_id, limit=1):
            if message.text and "String Session Generated Successfully" in message.text:
                await message.delete()
                logger.info(f"Deleted string session message for user: {chat_id}")
                break
    except Exception as e:
        logger.error(f"Error deleting message for user {chat_id}: {e}")
