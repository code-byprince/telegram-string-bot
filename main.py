"""
Main entry point for the application
"""

import asyncio
import sys
import os
from app.bot import create_app
from app.utils.logger import setup_logger
from app.config import Config

logger = setup_logger(__name__)


async def main():
    """Main entry point"""
    try:
        print("=" * 50)
        print("🚀 Starting String Generator Bot")
        print("=" * 50)
        
        # Check environment variables
        print("\n📋 Checking Environment Variables:")
        print(f"BOT_TOKEN: {'✅ Set' if Config.BOT_TOKEN else '❌ MISSING'}")
        print(f"ADMIN_IDS: {Config.ADMIN_IDS if Config.ADMIN_IDS else '❌ MISSING'}")
        print(f"API_ID: {Config.API_ID}")
        print(f"API_HASH: {'✅ Set' if Config.API_HASH else '❌ MISSING'}")
        print(f"LOG_LEVEL: {Config.LOG_LEVEL}")
        print("=" * 50)
        
        # Check if BOT_TOKEN is set
        if not Config.BOT_TOKEN:
            print("\n❌ ERROR: BOT_TOKEN is required!")
            print("Please set BOT_TOKEN in environment variables.")
            sys.exit(1)
        
        if not Config.ADMIN_IDS:
            print("\n⚠️ WARNING: No ADMIN_IDS set!")
            print("Admin commands will not work.")
        
        # Create and run bot
        print("\n✅ Starting bot...")
        bot = create_app()
        await bot.run()
        
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
