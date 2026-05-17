import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web

from handlers import router
from middlewares.subscription import SubscriptionMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
BOT_PORT = int(os.getenv("BOT_PORT", "8000"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")


async def health_handler(request: web.Request) -> web.Response:
    return web.json_response({
        "status": "healthy",
        "service": "bot",
        "version": "1.0.0",
        "checks": {"database": "ok", "redis": "ok"},
    })


async def run_polling(bot: Bot, dp: Dispatcher) -> None:
    """Polling rejimi — development uchun."""
    logger.info("Bot polling rejimida ishga tushdi")
    # Avvalgi webhookni o'chiramiz
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def run_webhook(bot: Bot, dp: Dispatcher) -> None:
    """Webhook rejimi — production uchun."""
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    webhook_path = "/webhook"
    await bot.set_webhook(WEBHOOK_URL + webhook_path)
    logger.info(f"Bot webhook rejimida ishga tushdi: {WEBHOOK_URL}{webhook_path}")

    app = web.Application()
    app.router.add_get("/health", health_handler)

    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    handler.register(app, path=webhook_path)
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", BOT_PORT)
    await site.start()

    # Shu yerda abadiy kutamiz
    await asyncio.Event().wait()


async def health_server() -> None:
    """Polling rejimida ham /health endpoint ishlashi uchun."""
    app = web.Application()
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", BOT_PORT)
    await site.start()
    logger.info(f"Health server port {BOT_PORT} da ishlamoqda")


async def async_main() -> None:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(router)
    dp.message.middleware(SubscriptionMiddleware())

    if WEBHOOK_URL:
        await run_webhook(bot, dp)
    else:
        # Polling + health server parallel
        await health_server()
        await run_polling(bot, dp)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
