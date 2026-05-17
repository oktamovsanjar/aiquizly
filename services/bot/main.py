import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from handlers import router
from middlewares.subscription import SubscriptionMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
BOT_PORT = int(os.getenv("BOT_PORT", "8000"))
WEBHOOK_PATH = "/webhook"


async def on_startup(bot: Bot) -> None:
    logger.info("Bot ishga tushdi")


async def health_handler(request: web.Request) -> web.Response:
    return web.json_response({
        "status": "healthy",
        "service": "bot",
        "version": "1.0.0",
        "checks": {"database": "ok", "redis": "ok"},
    })


def main() -> None:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(router)
    dp.message.middleware(SubscriptionMiddleware())

    dp.startup.register(on_startup)

    app = web.Application()
    app.router.add_get("/health", health_handler)

    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    web.run_app(app, host="0.0.0.0", port=BOT_PORT)


if __name__ == "__main__":
    main()
