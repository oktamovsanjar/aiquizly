import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from utils.api import subscription_client

logger = logging.getLogger(__name__)

_PAYWALL_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data="pay:monthly")],
        [
            InlineKeyboardButton(
                text="👥 Taklif qilib yutish", callback_data="ref:invite"
            )
        ],
    ]
)

_PAYWALL_TEXT = (
    "Bu oyda 3/3 fayl yuklagansiz.\n\n"
    "💎 Premium bilan:\n"
    "• Cheksiz fayl yuklash\n"
    "• Guruhga ulashish\n"
    "• Quiz doim saqlanadi\n\n"
    "💰 29,000 so'm/oy  |  249,000 so'm/yil\n\n"
    "Yoki 3 ta do'st taklif qiling = 9 kun bepul!"
)


class SubscriptionMiddleware(BaseMiddleware):
    """
    Faylni yuklash so'rovida limit tekshiriladi.
    Limit oshgan bo'lsa premium taklif xabari yuboriladi.
    """

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if event.document is not None:
            allowed = await subscription_client().check_limit(event.from_user.id)
            if not allowed:
                await event.answer(_PAYWALL_TEXT, reply_markup=_PAYWALL_KB)
                return
        return await handler(event, data)
