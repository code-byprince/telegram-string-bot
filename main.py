"""
Main entry point for the application
"""

import asyncio
import threading
import sys
import os
from app.bot import create_app
from web.app import app as web_app
from app.utils.logger import setup_logger
from app.config import Config

logger = setup_logger(__name__)


def run_web_server():
    """Run Flask web server in a separate thread"""
    try:
        logger.info(f"Starting web server on {Config.HOST}:{Config.PORT}")
        web_app.run(host=Config.HOST, port=Config.PORT, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Failed to start web server: {e}")


async def main():
    """Main entry point"""
    try:
        # Log configuration (without sensitive data)
        logger.info("Starting String Generator Bot")
        logger.info(f"Configuration loaded: {Config.get_config_dict()}")
        
        # Check if BOT_TOKEN is set
        if not Config.BOT_TOKEN:
            logger.error("BOT_TOKEN is required. Please set it in environment variables.")
            sys.exit(1)
        
        # Start web server in a separate thread
        web_thread = threading.Thread(target=run_web_server, daemon=True)
        web_thread.start()
        
        # Create and run bot
        bot = create_app()
        await bot.run()
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
