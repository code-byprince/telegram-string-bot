from pyrogram import Client

from app.config import Config
from app.utils.logger import log
from app.handlers import start, generate, admin


def create_bot() -> Client:
    Config.validate()

    app = Client(
        name="session_generator_bot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN,
        in_memory=True,  # the bot's own session is also never written to disk
    )

    start.register(app)
    generate.register(app)
    admin.register(app, generate.state_manager)

    log.info("Handlers registered.")
    return app
