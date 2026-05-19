from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select, update

from db import AsyncSessionLocal
from db.models import Referral, User
from keyboards.main_menu import main_menu_keyboard
from keyboards.language import language_keyboard
from utils.admin_notify import notify_new_user
from utils.i18n import t
from utils.api import ai_engine_client

router = Router()

REFERRAL_XP_REFERRER = 50  # taklif qilganga
REFERRAL_XP_REFERRED = 20  # yangi foydalanuvchiga
REFERRAL_PREMIUM_DAYS = 3  # taklif qilganga premium kunlar


async def _upsert_user(message: Message) -> tuple[User, bool]:
    """Foydalanuvchini DB ga qo'shish yoki yangilash. (User, is_new) qaytaradi."""
    tg = message.from_user
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg.id))
        user = result.scalar_one_or_none()
        is_new = user is None
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
        return user, is_new


async def _process_referral(
    referred_user: User, referrer_telegram_id: int
) -> str | None:
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

        await game_client().award_xp(
            referrer.telegram_id, REFERRAL_XP_REFERRER, "referral"
        )
        await game_client().award_xp(
            referred_user.telegram_id, REFERRAL_XP_REFERRED, "referral_join"
        )
    except Exception:
        pass

    return referrer.first_name or referrer.username or "Do'stingiz"


@router.message(CommandStart(deep_link=True, magic=F.args.startswith("quiz_")))
async def cmd_start_quiz(message: Message, state: FSMContext, command: CommandObject) -> None:
    """Deep link orqali quiz ochish: /start quiz_<quiz_id>"""
    quiz_id = (command.args or "")[5:]
    user, is_new = await _upsert_user(message)

    # Yangi user — avval til tanlashi kerak, quiz_id ni saqlaymiz
    if is_new or not _is_returning_user(user):
        lang = message.from_user.language_code or "uz"
        if lang not in ("uz", "ru", "en"):
            lang = "uz"
        await state.update_data(pending_quiz_id=quiz_id)
        await message.answer(
            t("welcome_new", lang),
            reply_markup=language_keyboard(),
        )
        return

    # Mavjud user — darhol quizga yo'naltirish
    await _open_quiz_by_id(message, state, quiz_id, user.language_code or "uz")


@router.message(CommandStart(deep_link=True, magic=F.args.startswith("ref_")))
async def cmd_start_referral(message: Message, command: CommandObject) -> None:
    """Deep link orqali kirish: /start ref_<telegram_id>"""
    args = command.args or ""
    try:
        referrer_tg_id = int(args[4:])  # "ref_" ni olib tashlaymiz
    except (ValueError, IndexError):
        await cmd_start(message)
        return

    user, is_new = await _upsert_user(message)
    if is_new:
        import asyncio

        asyncio.create_task(
            notify_new_user(
                message.bot,
                user.telegram_id,
                user.username,
                user.first_name,
                params=[f"ref_{referrer_tg_id}"],
            )
        )
    referrer_name = await _process_referral(user, referrer_tg_id)

    bonus_text = ""
    lang = message.from_user.language_code or "uz"
    if lang not in ("uz", "ru", "en"):
        lang = "uz"
    if referrer_name:
        bonus_text = t(
            "referral_bonus", lang, name=referrer_name, xp=REFERRAL_XP_REFERRED
        )

    await message.answer(
        t("welcome_new", lang) + bonus_text,
        reply_markup=language_keyboard(),
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Birinchi kirish yoki qayta kirish."""
    user, is_new = await _upsert_user(message)
    if is_new:
        import asyncio

        asyncio.create_task(
            notify_new_user(
                message.bot,
                user.telegram_id,
                user.username,
                user.first_name,
            )
        )

    # Foydalanuvchi allaqachon ro'yxatdan o'tgan bo'lsa — menyu ko'rsat
    if _is_returning_user(user):
        lang = user.language_code or "uz"
        # FSM state ga tilni saqlash
        await state.update_data(language_code=lang)
        await message.answer(
            _welcome_back_text(lang, message.from_user.first_name),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    lang = message.from_user.language_code or "uz"
    if lang not in ("uz", "ru", "en"):
        lang = "uz"
    await message.answer(
        t("welcome_new", lang),
        reply_markup=language_keyboard(),
    )


async def _open_quiz_by_id(
    message: Message, state: FSMContext, quiz_id: str, lang: str
) -> None:
    from fsm.states import QuizStates
    from utils.api import ai_engine_client
    from keyboards.inline import set_select_keyboard

    try:
        quiz = await ai_engine_client().get_quiz(quiz_id)
        title = quiz.get("title", quiz.get("name", "Quiz"))
        total_q = quiz.get("total_questions", 0)
        set_size = 20
        num_sets = max(1, (total_q + set_size - 1) // set_size)
        sets = [
            {"set_number": i + 1, "question_count": min(set_size, total_q - i * set_size)}
            for i in range(num_sets)
        ]
    except Exception:
        await message.answer("❌ Quiz topilmadi.")
        return

    await state.set_state(QuizStates.BROWSING_MY_QUIZZES)
    await state.update_data(
        language_code=lang, selected_quiz_id=quiz_id, selected_quiz_title=title,
        quiz_id=quiz_id, quiz_title=title,
    )
    await message.answer(
        f"📋 <b>{title}</b>\n"
        f"📏 {total_q} savol | {num_sets} set\n\n"
        "Set tanlang:",
        reply_markup=set_select_keyboard(sets, quiz_id),
    )


def _is_returning_user(user) -> bool:
    """Foydalanuvchi avval ham kirgan (created_at va updated_at farqli)."""
    try:
        return user.updated_at != user.created_at
    except Exception:
        return False


def _welcome_back_text(lang: str, name: str | None) -> str:
    return t("welcome_back", lang, name=name or "")


async def _suggest_top_quiz(message: Message, lang: str) -> None:
    """Yangi user uchun bugungi eng mashhur quizni taklif qiladi."""
    try:
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        data = await ai_engine_client().get_quizzes(public=True, page_size=5)
        quizzes = data.get("quizzes", []) if isinstance(data, dict) else []
        if not quizzes:
            return
        # Eng ko'p o'ynalgan (play_count bo'yicha)
        top = max(quizzes, key=lambda q: q.get("play_count", 0))
        quiz_id = top.get("id", "")
        title = top.get("title", "Quiz")[:40]
        total_q = top.get("total_questions", 0)
        play_count = top.get("play_count", 0)
        if not quiz_id:
            return

        me = await message.bot.get_me()
        link = f"https://t.me/{me.username}?start=quiz_{quiz_id}"

        texts = {
            "uz": f"🔥 <b>Bugungi mashhur quiz:</b>\n\n📋 <b>{title}</b>\n📊 {total_q} savol · {play_count} marta o'ynaldi\n\nHoziroq sinab ko'ring!",
            "ru": f"🔥 <b>Популярный квиз сегодня:</b>\n\n📋 <b>{title}</b>\n📊 {total_q} вопросов · сыграно {play_count} раз\n\nПопробуйте сейчас!",
            "en": f"🔥 <b>Today's popular quiz:</b>\n\n📋 <b>{title}</b>\n📊 {total_q} questions · played {play_count} times\n\nTry it now!",
        }
        btn_texts = {"uz": "▶️ O'ynash", "ru": "▶️ Играть", "en": "▶️ Play"}

        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=btn_texts.get(lang, "▶️ O'ynash"), url=link)
        ]])
        await message.answer(texts.get(lang, texts["uz"]), reply_markup=kb)
    except Exception:
        pass


@router.message(F.text.in_({"O'zbek", "Русский", "English"}))
async def choose_language(message: Message, state: FSMContext) -> None:
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

    # FSM state ga ham saqlash — boshqa handlerlar uchun
    data = await state.get_data()
    await state.update_data(language_code=lang)

    # Deep link orqali kelgan quiz bormi?
    pending_quiz_id = data.get("pending_quiz_id")
    if pending_quiz_id:
        await state.update_data(pending_quiz_id=None)
        await message.answer(
            t("language_saved", lang), reply_markup=main_menu_keyboard(lang)
        )
        await _open_quiz_by_id(message, state, pending_quiz_id, lang)
        return

    await message.answer(
        t("language_saved", lang),
        reply_markup=main_menu_keyboard(lang),
    )

    # Yangi user uchun bugungi eng mashhur quizni taklif qilish
    await _suggest_top_quiz(message, lang)
