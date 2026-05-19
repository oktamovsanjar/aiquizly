"""Kunlik bildirishnomalar — APScheduler orqali."""
import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text

logger = logging.getLogger(__name__)

TASHKENT = pytz.timezone("Asia/Tashkent")
REDIS_DAILY_KEY = "scheduler:daily_quiz_sent"


async def _push_notification(redis_client, telegram_id: int, text: str, buttons: list = None):
    """Notifier Redis queue ga xabar qo'shadi."""
    n = {
        "user_telegram_id": telegram_id,
        "text": text,
        "parse_mode": "HTML",
        "inline_buttons": buttons or [],
    }
    await redis_client.rpush("notification:queue", json.dumps(n, ensure_ascii=False))


async def daily_quiz_reminder(bot, db_session_factory, redis_client):
    """Har kuni 18:00 da oxirgi 24 soatda o'ynamagan userlarga taklif yuboradi."""
    logger.info("Kunlik quiz taklif boshlandi")

    today_key = datetime.now(TASHKENT).strftime("%Y-%m-%d")
    already = await redis_client.get(f"{REDIS_DAILY_KEY}:{today_key}")
    if already:
        logger.info("Bugun allaqachon yuborilgan, skip")
        return

    try:
        async with db_session_factory() as session:
            # Oxirgi 24 soatda o'ynamagan, bot bloklamagan userlar
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            rows = await session.execute(
                text("""
                    SELECT u.telegram_id, u.first_name, u.language_code
                    FROM users u
                    WHERE u.is_bot_blocked = false
                      AND u.telegram_id IS NOT NULL
                      AND (u.last_active_at IS NULL OR u.last_active_at < :cutoff)
                    LIMIT 1000
                """),
                {"cutoff": cutoff},
            )
            users = rows.fetchall()

        # Eng mashhur quiz ni olish
        try:
            from utils.api import ai_engine_client
            data = await ai_engine_client().get_quizzes(public=True, page_size=1)
            quizzes = data.get("quizzes", []) if isinstance(data, dict) else []
            top_quiz = quizzes[0] if quizzes else None
        except Exception:
            top_quiz = None

        sent = 0
        bot_me = await bot.get_me()
        bot_username = bot_me.username or "aiquizlybot"

        for row in users:
            telegram_id, first_name, lang = row[0], row[1] or "", row[2] or "uz"
            name = first_name.split()[0] if first_name else "Salom"

            if lang == "ru":
                text_msg = f"👋 <b>{name}</b>, вы давно не играли!\n\nСыграйте в квиз сегодня и поднимитесь в рейтинге 🏆"
            elif lang == "en":
                text_msg = f"👋 <b>{name}</b>, you haven't played in a while!\n\nPlay a quiz today and climb the leaderboard 🏆"
            else:
                text_msg = f"👋 <b>{name}</b>, bugun hali quiz o'ynadingizmi?\n\nReyting uchun o'ynang va o'z o'rningizni egallang 🏆"

            buttons = [{"text": "▶️ Quiz o'ynash", "url": f"https://t.me/{bot_username}"}]
            if top_quiz:
                quiz_id = top_quiz.get("id", "")
                quiz_title = top_quiz.get("title", "Quiz")[:30]
                buttons.append({
                    "text": f"📋 {quiz_title}",
                    "url": f"https://t.me/{bot_username}?start=quiz_{quiz_id}",
                })

            await _push_notification(redis_client, telegram_id, text_msg, buttons)
            sent += 1
            if sent % 30 == 0:
                await asyncio.sleep(1)  # rate limit

        # Bugun yuborilganligini belgilaymiz (24 soat)
        await redis_client.setex(f"{REDIS_DAILY_KEY}:{today_key}", 86400, "1")
        logger.info("Kunlik taklif yuborildi: %d ta user", sent)

    except Exception as e:
        logger.error("Kunlik taklif xatosi: %s", e, exc_info=True)


def setup_scheduler(bot, db_session_factory, redis_client) -> AsyncIOScheduler:
    """APScheduler ni sozlaydi va qaytaradi."""
    scheduler = AsyncIOScheduler(timezone=TASHKENT)

    # Har kuni soat 18:00 Toshkent vaqtida
    scheduler.add_job(
        daily_quiz_reminder,
        trigger="cron",
        hour=18,
        minute=0,
        args=[bot, db_session_factory, redis_client],
        id="daily_quiz_reminder",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    logger.info("Scheduler sozlandi: kunlik taklif 18:00 (Toshkent)")
    return scheduler
