from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy import select, update

from db import AsyncSessionLocal
from db.models import User
from keyboards.main_menu import main_menu_keyboard
from keyboards.language import language_keyboard

router = Router()


async def _upsert_user(message: Message) -> None:
    """Foydalanuvchini DB ga qo'shish yoki yangilash."""
    tg = message.from_user
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg.id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_id=tg.id,
                username=tg.username,
                first_name=tg.first_name,
                last_name=tg.last_name,
                language_code=tg.language_code or "uz",
            )
            session.add(user)
        else:
            await session.execute(
                update(User)
                .where(User.telegram_id == tg.id)
                .values(
                    username=tg.username,
                    first_name=tg.first_name,
                    last_name=tg.last_name,
                )
            )
        await session.commit()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Birinchi kirish — foydalanuvchini ro'yxatdan o'tkazish va til tanlash"""
    await _upsert_user(message)
    await message.answer(
        "Quiz Bot ga xush kelibsiz!\n\n"
        "Bu bot orqali:\n"
        "• Tayyor quizlarni yechishingiz\n"
        "• O'z testlaringizni yaratishingiz\n"
        "• Do'stlar bilan bellashishingiz mumkin\n\n"
        "Tilni tanlang:",
        reply_markup=language_keyboard(),
    )


@router.message(F.text.in_({"O'zbek", "Русский", "English"}))
async def choose_language(message: Message) -> None:
    """Til tanlangandan keyin asosiy menyu"""
    lang_map = {"O'zbek": "uz", "Русский": "ru", "English": "en"}
    lang = lang_map.get(message.text, "uz")

    # Tilni DB ga saqlash
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User)
            .where(User.telegram_id == message.from_user.id)
            .values(language_code=lang)
        )
        await session.commit()

    await message.answer(
        "Asosiy menyu:",
        reply_markup=main_menu_keyboard(lang),
    )
