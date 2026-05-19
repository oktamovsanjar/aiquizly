import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import (
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeAllGroupChats,
)
from aiohttp import web

from handlers import router
from handlers.quiz import on_poll_answer
from middlewares.subscription import SubscriptionMiddleware
from utils.admin_notify import notify_bot_started

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
BOT_PORT = int(os.getenv("BOT_PORT", "8000"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")


async def health_handler(request: web.Request) -> web.Response:
    return web.json_response(
        {
            "status": "healthy",
            "service": "bot",
            "version": "1.0.0",
            "checks": {"database": "ok", "redis": "ok"},
        }
    )


async def run_polling(bot: Bot, dp: Dispatcher) -> None:
    """Polling rejimi — development uchun."""
    logger.info("Bot polling rejimida ishga tushdi")
    # Avvalgi webhookni o'chiramiz
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(
        bot,
        allowed_updates=[
            "message",
            "callback_query",
            "poll_answer",
            "poll",
            "inline_query",
            "chosen_inline_result",
            "my_chat_member",
            "chat_member",
        ],
    )


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


async def _setup_bot_settings(bot: Bot) -> None:
    """BotFather orqali sozlanadigan barcha parametrlarni kod orqali o'rnatish."""

    # ── Private chat commands ──────────────────────────────────────────
    private_uz = [
        BotCommand(command="start", description="🏠 Botni boshlash / Menyuga qaytish"),
        BotCommand(command="quiz", description="▶️ Quiz o'ynash"),
        BotCommand(command="create", description="📤 Quiz yaratish (fayl yuklash)"),
        BotCommand(command="profile", description="👤 Profilim va statistika"),
        BotCommand(command="top", description="🏆 Reyting jadval"),
        BotCommand(command="invite", description="👥 Do'st taklif qilish"),
        BotCommand(command="stop", description="⏹ Quizni to'xtatish"),
        BotCommand(command="help", description="❓ Yordam"),
    ]
    private_ru = [
        BotCommand(command="start", description="🏠 Запустить бота / Главное меню"),
        BotCommand(command="quiz", description="▶️ Играть в квиз"),
        BotCommand(command="create", description="📤 Создать квиз (загрузка файла)"),
        BotCommand(command="profile", description="👤 Мой профиль и статистика"),
        BotCommand(command="top", description="🏆 Таблица лидеров"),
        BotCommand(command="invite", description="👥 Пригласить друга"),
        BotCommand(command="stop", description="⏹ Остановить квиз"),
        BotCommand(command="help", description="❓ Помощь"),
    ]
    private_en = [
        BotCommand(command="start", description="🏠 Start bot / Main menu"),
        BotCommand(command="quiz", description="▶️ Play a quiz"),
        BotCommand(command="create", description="📤 Create quiz (upload file)"),
        BotCommand(command="profile", description="👤 My profile & stats"),
        BotCommand(command="top", description="🏆 Leaderboard"),
        BotCommand(command="invite", description="👥 Invite a friend"),
        BotCommand(command="stop", description="⏹ Stop quiz"),
        BotCommand(command="help", description="❓ Help"),
    ]

    # ── Group chat commands ────────────────────────────────────────────
    group_commands = [
        BotCommand(command="quiz", description="▶️ Guruhda quiz boshlash"),
        BotCommand(command="stop", description="⏹ Quizni to'xtatish (admin)"),
        BotCommand(command="top", description="🏆 Guruh reytingi"),
        BotCommand(command="settings", description="⚙️ Guruh sozlamalari (admin)"),
    ]

    await asyncio.gather(
        bot.set_my_commands(private_uz, scope=BotCommandScopeDefault()),
        bot.set_my_commands(
            private_ru, scope=BotCommandScopeDefault(), language_code="ru"
        ),
        bot.set_my_commands(
            private_en, scope=BotCommandScopeDefault(), language_code="en"
        ),
        bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats()),
    )

    # ── Bot tavsifi (BotFather → /setdescription) ─────────────────────
    await bot.set_my_description(
        "🤖 AI Quiz Bot — fayldan avtomatik test yaratadi.\n\n"
        "📄 PDF, DOCX, XLSX, TXT fayllarni yuboring — AI savollarni o'zi ajratib, "
        "tayyor quiz hosil qiladi. O'ynang, reyting yig'ing, do'stlaringizni taklif qiling!"
    )
    await bot.set_my_description(
        "🤖 AI Quiz Bot — автоматически создаёт тесты из файлов.\n\n"
        "📄 Отправьте PDF, DOCX, XLSX или TXT — ИИ сам выделит вопросы и создаст квиз. "
        "Играйте, набирайте очки, приглашайте друзей!",
        language_code="ru",
    )
    await bot.set_my_description(
        "🤖 AI Quiz Bot — creates quizzes automatically from your files.\n\n"
        "📄 Send a PDF, DOCX, XLSX or TXT — AI extracts questions and builds a ready quiz. "
        "Play, earn XP, climb the leaderboard!",
        language_code="en",
    )

    # ── Qisqa tavsif (profil ekranida ko'rinadi) ──────────────────────
    await bot.set_my_short_description("📄 Fayldan AI yordamida quiz yarating")
    await bot.set_my_short_description(
        "📄 Создайте квиз из файла с помощью ИИ", language_code="ru"
    )
    await bot.set_my_short_description(
        "📄 Create AI-powered quizzes from your files", language_code="en"
    )

    logger.info("Bot settings sozlandi")


async def async_main() -> None:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/3")
    storage = RedisStorage.from_url(redis_url)
    dp = Dispatcher(storage=storage)

    dp.include_router(router)
    dp.poll_answer.register(
        on_poll_answer
    )  # aiogram 3.7: sub-router poll_answer dp ga o'tmaydi
    dp.message.middleware(SubscriptionMiddleware())

    try:
        await _setup_bot_settings(bot)
    except Exception as e:
        logger.warning("Bot settings sozlanmadi: %s", e)

    if WEBHOOK_URL:
        try:
            await notify_bot_started(bot, mode="webhook")
        except Exception:
            pass
        await run_webhook(bot, dp)
    else:
        # Polling + health server parallel
        await health_server()
        try:
            await notify_bot_started(bot, mode="polling")
        except Exception:
            pass
        await run_polling(bot, dp)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
