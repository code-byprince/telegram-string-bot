"""
Entrypoint.

Runs a minimal Flask server (for Render's health check) on a background
thread, and the Pyrogram bot on the main thread/event loop.
"""

import threading

from app.config import Config
from app.utils.logger import log
from app.bot import create_bot
from app.web.health import flask_app


def run_flask():
    # threaded=True lets the health check respond even while the bot is busy.
    flask_app.run(host="0.0.0.0", port=Config.PORT, threaded=True, use_reloader=False)


def main():
    Config.validate()

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    log.info(f"Health check server started on port {Config.PORT}")

    bot = create_bot()
    log.info("Starting Telegram bot...")
    bot.run()


if __name__ == "__main__":
    main()
