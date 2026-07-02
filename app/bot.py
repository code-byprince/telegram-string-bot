"""
Bot initialization and main application
"""

import asyncio
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from app.config import Config
from app.handlers import start, generate, admin, cancel
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class StringGeneratorBot:
    """Main bot class"""
    
    def __init__(self):
        self.client = None
        self.is_running = False
    
    async def start(self):
        """Start the bot"""
        if self.is_running:
            logger.warning("Bot is already running")
            return
        
        try:
            self.client = Client(
                "string_generator_bot",
                bot_token=Config.BOT_TOKEN,
                api_id=Config.API_ID or 6,  # Default API ID for testing
                api_hash=Config.API_HASH or "your_api_hash",
                workers=4,
                parse_mode="html"
            )
            
            # Register handlers
            self._register_handlers()
            
            # Start the client
            await self.client.start()
            self.is_running = True
            
            logger.info("Bot started successfully!")
            
            # Get bot info
            me = await self.client.get_me()
            logger.info(f"Bot: @{me.username} | ID: {me.id}")
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise
    
    def _register_handlers(self):
        """Register all message and callback handlers"""
        
        # Start command
        self.client.add_handler(
            MessageHandler(start.start_command, filters.command("start"))
        )
        
        # Cancel command
        self.client.add_handler(
            MessageHandler(cancel.cancel_command, filters.command("cancel"))
        )
        
        # Generate command
        self.client.add_handler(
            MessageHandler(generate.generate_command, filters.command("generate"))
        )
        
        # Admin commands
        self.client.add_handler(
            MessageHandler(admin.stats_command, filters.command("stats") & filters.user(Config.ADMIN_IDS))
        )
        self.client.add_handler(
            MessageHandler(admin.broadcast_command, filters.command("broadcast") & filters.user(Config.ADMIN_IDS))
        )
        self.client.add_handler(
            MessageHandler(admin.users_command, filters.command("users") & filters.user(Config.ADMIN_IDS))
        )
        
        # Text message handler (for conversation)
        self.client.add_handler(
            MessageHandler(generate.text_message_handler, filters.text & filters.private & ~filters.command([]))
        )
        
        # Callback query handler
        self.client.add_handler(
            CallbackQueryHandler(generate.callback_handler)
        )
    
    async def stop(self):
        """Stop the bot"""
        if self.client and self.is_running:
            await self.client.stop()
            self.is_running = False
            logger.info("Bot stopped")
    
    async def run(self):
        """Run the bot indefinitely"""
        try:
            await self.start()
            logger.info("Bot is now running. Press Ctrl+C to stop.")
            await asyncio.Event().wait()  # Wait forever
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            await self.stop()


def create_app():
    """Factory function to create bot instance"""
    return StringGeneratorBot()
