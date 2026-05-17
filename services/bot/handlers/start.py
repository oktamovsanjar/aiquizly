import uuid as uuid_mod

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy import select, update

from db import AsyncSessionLocal
from db.models import Referral, User
from keyboards.main_menu import main_menu_keyboard
from keyboards.language import language_keyboard

router = Router()

REFERRAL_XP_REFERRER = 50      # taklif qilganga
REFERRAL_XP_REFERRED = 20      # yangi foydalanuvchiga
REFERRAL_PREMIUM_DAYS = 3      # taklif qilganga premium kunlar


async def _upsert_user(message: Message) -> User:
    """Foydalanuvchini DB ga qo'shish yoki yangilash. User qaytaradi."""
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
            await session.commit()
            await session.refresh(user)
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
        return user


async def _process_referral(referred_user: User, referrer_telegram_id: int) -> str | None:
    """
    Referral bonus berish:
    - Referrer: +50 XP + 3 kun premium (subscription servis orqali)
    - Referred: +20 XP bonus
    Qaytaradi: referrer first_name (xabar uchun) yoki None
    """
    if referred_user.telegram_id == referrer_telegram_id:
        return None  # O'z-o'ziga referral bo'lmaydi

    async with AsyncSessionLocal() as session:
        # Referrer ni topamiz
        ref_result = await session.execute(
            select(User).where(User.telegram_id == referrer_telegram_id)
        )
        referrer = ref_result.scalar_one_or_none()
        if not referrer:
            return None

        # Dublikat tekshirish
        dup = await session.execute(
            select(Referral).where(
                Referral.referrer_id == referrer.id,
                Referral.referred_id == referred_user.id,
            )
        )
        if dup.scalar_one_or_none():
            return None  # Allaqachon ishlatilgan

        # Referral yozuvi
        ref_record = Referral(
            referrer_id=referrer.id,
            referred_id=referred_user.id,
            bonus_given=False,
            bonus_days=REFERRAL_PREMIUM_DAYS,
        )
        session.add(ref_record)

        # referred_user ga referrer ni bog'lash
        referred_user_db = await session.get(User, referred_user.id)
        if referred_user_db and not referred_user_db.referred_by:
            referred_user_db.referred_by = referrer.id

        await session.commit()

    # Subscription servisga bonus so'rovi
    try:
        from utils.api import subscription_client
        await subscription_client().activate_premium(
            user_id=referrer.telegram_id,
            days=REFERRAL_PREMIUM_DAYS,
            source="referral",
        )
    except Exception:
        pass  # Fail-open: bonus servis ishlamasa ham ro'yxatga olindi

    # XP berish (game servis orqali)
    try:
        from utils.api import game_client
        await game_client().award_xp(referrer.telegram_id, REFERRAL_XP_REFERRER, "referral")
        await game_client().award_xp(referred_user.telegram_id, REFERRAL_XP_REFERRED, "referral_join")
    except Exception:
        pass

    return referrer.first_name or referrer.username or "Do'stingiz"


@router.message(CommandStart(deep_link=True, magic=F.args.startswith("ref_")))
async def cmd_start_referral(message: Message) -> None:
    """Deep link orqali kirish: /start ref_<telegram_id>"""
    args = message.args  # "ref_123456789"
    try:
        referrer_tg_id = int(args[4:])  # "ref_" ni olib tashlaymiz
    except (ValueError, IndexError):
        await cmd_start(message)
        return

    user = await _upsert_user(message)
    referrer_name = await _process_referral(user, referrer_tg_id)

    bonus_text = ""
    if referrer_name:
        bonus_text = (
            f"\n\n🎁 <b>{referrer_name}</b> taklifi orqali keldingiz!\n"
            f"Siz: <b>+{REFERRAL_XP_REFERRED} XP</b> bonus oldingiz!"
        )

    await message.answer(
        f"Quiz Bot ga xush kelibsiz!{bonus_text}\n\n"
        "Tilni tanlang:",
        reply_markup=language_keyboard(),
    )


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
