import httpx
import os
import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message

logger = logging.getLogger(__name__)

SUBSCRIPTION_URL = os.getenv("SUBSCRIPTION_URL", "http://subscription:8003")

# Limit tekshirish faqat shu action lar uchun
LIMIT_CHECKED_ACTIONS = {"file_upload"}


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
        # Faqat fayl yuklash hodisalarida limit tekshiriladi
        if event.document is not None:
            allowed = await self._check_limit(event.from_user.id)
            if not allowed:
                await event.answer(
                    "Bu oyda fayl yuklash limitingiz tugadi.\n\n"
                    "Premium bilan:\n"
                    "• Cheksiz yuklash\n"
                    "• Guruhga ulashish\n"
                    "• Quiz doim saqlanadi\n\n"
                    "💰 29,000 so'm/oy"
                    # TODO: to'lov tugmalarini qo'shish
                )
                return
        return await handler(event, data)

    async def _check_limit(self, telegram_id: int) -> bool:
        """Subscription servisdan limit tekshiradi. True = ruxsat bor."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{SUBSCRIPTION_URL}/limits/check",
                    params={"telegram_id": telegram_id, "action": "file_upload"},
                )
                if resp.status_code == 200:
                    return resp.json().get("allowed", True)
        except httpx.HTTPError as e:
            logger.warning("Subscription servis bilan bog'lanib bo'lmadi: %s", e)
            # Agar servis ishlamasa — ruxsat beramiz (fail open)
            return True
        return True
