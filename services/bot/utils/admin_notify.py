"""Admin notification utility — barcha xizmat xabarlari uchun."""
from __future__ import annotations

import logging
import os
from datetime import datetime

from aiogram import Bot

logger = logging.getLogger(__name__)

ADMIN_ID: int = int(os.getenv("ADMIN_TELEGRAM_ID", "7537966029"))


async def notify_admin(bot: Bot, text: str) -> None:
    """Admin ga oddiy matn xabar yuboradi. Xato bo'lsa jimgina o'tkazib yuboradi."""
    try:
        await bot.send_message(ADMIN_ID, text, parse_mode="HTML")
    except Exception as exc:
        logger.warning("admin_notify failed: %s", exc)


async def notify_bot_started(bot: Bot, mode: str = "polling") -> None:
    me = await bot.get_me()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = (
        f"✅ <b>Bot ishga tushdi!</b>\n\n"
        f"🤖 @{me.username}\n"
        f"🕐 {now}\n"
        f"⚙️ Rejim: <code>{mode}</code>"
    )
    await notify_admin(bot, text)


async def notify_new_user(bot: Bot, user_id: int, username: str | None,
                          first_name: str | None, params: list[str] | None = None) -> None:
    uname = f"@{username}" if username else "—"
    name = first_name or "—"
    param_str = str(params) if params else "[]"
    text = (
        f"👤 <b>Yangi foydalanuvchi botga qo'shildi!</b>\n\n"
        f"👤 Ism: {name} ({uname})\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"🚀 Parametrlar: <code>{param_str}</code>"
    )
    await notify_admin(bot, text)
