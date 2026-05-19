"""
Bot buyruqlari handlerlari — BOT_UX.md §21

/help     — Yordam
/settings — Sozlamalar
/cancel   — Bekor qilish
/quiz     — Tez quiz
"""

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from fsm.states import QuizStates
from keyboards.main_menu import main_menu_keyboard
from utils.i18n import t

router = Router()

# Barcha til variantlari bilan asosiy menyu tugmalari
_ALL_MENU_BUTTONS = {
    "▶️ Boshlash",
    "🔍 Qidirish",
    "📤 Quiz Yaratish",
    "🏆 Reyting",
    "👤 Profil",
    "👥 Taklif qilish",
    "▶️ Начать",
    "🔍 Поиск",
    "📤 Создать квиз",
    "🏆 Рейтинг",
    "👤 Профиль",
    "👥 Пригласить",
    "▶️ Start",
    "🔍 Search",
    "📤 Create Quiz",
    "🏆 Leaderboard",
    "👤 Profile",
    "👥 Invite",
}


@router.message(~StateFilter(None), F.text.in_(_ALL_MENU_BUTTONS))
async def menu_button_in_state(message: Message, state: FSMContext) -> None:
    """
    FSM state da bo'lganda asosiy menyu tugmasi bosilsa —
    state tozalanadi va to'g'ri javob beriladi.
    StateFilter(None) emas — ya'ni faqat state mavjud bo'lganda ishlaydi.
    """
    await state.clear()
    text = message.text

    if text in {"▶️ Boshlash", "▶️ Начать", "▶️ Start"}:
        from keyboards.inline import quiz_browse_keyboard

        await message.answer("Qayerdan o'ynaysiz?", reply_markup=quiz_browse_keyboard())
    elif text in {"🔍 Qidirish", "🔍 Поиск", "🔍 Search"}:
        await state.set_state(QuizStates.SEARCHING)
        await message.answer("🔍 Qidiring yoki teg tanlang:\n\nYoki matn yozing...")
    elif text in {"🏆 Reyting", "🏆 Рейтинг", "🏆 Leaderboard"}:
        from handlers.profile import show_leaderboard

        await show_leaderboard(message)
    elif text in {"👤 Profil", "👤 Профиль", "👤 Profile"}:
        from handlers.profile import show_profile

        await show_profile(message, state)
    elif text in {"👥 Taklif qilish", "👥 Пригласить", "👥 Invite"}:
        from handlers.profile import show_referral

        await show_referral(message)
    elif text in {"📤 Quiz Yaratish", "📤 Создать квиз", "📤 Create Quiz"}:
        from handlers.upload import quiz_create_menu

        await quiz_create_menu(message, state)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>Quiz Bot — Yordam</b>\n\n"
        "📋 <b>Buyruqlar:</b>\n"
        "/start — Botni boshlash\n"
        "/quiz — Tez quiz (oxirgi to'plamdan)\n"
        "/create — Quiz yaratish (fayl yoki rasm)\n"
        "/profile — Profil va statistika\n"
        "/top — Reyting (leaderboard)\n"
        "/invite — Referal link\n"
        "/stop — Quizni to'xtatish\n"
        "/settings — Sozlamalar\n"
        "/help — Ushbu yordam\n"
        "/cancel — Amalni bekor qilish\n\n"
        "📤 <b>Fayl yuklash:</b>\n"
        "• .docx, .pdf, .xlsx, .txt — max 10 MB\n"
        "• Rasmlar: .jpg, .png\n\n"
        "🎮 <b>Quiz o'ynash:</b>\n"
        "• Har savol uchun vaqt: 15/30/45/60 son\n"
        "• 2 ta ketma-ket skip → avtomatik pauza\n"
        "• /stop — quizni to'xtatish\n\n"
        "❓ Savol bo'lsa: @support_bot\n"
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language_code", "uz")

    lang_display = {"uz": "🇺🇿 O'zbek", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}.get(
        lang, "🇺🇿 O'zbek"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="set:lang:uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set:lang:ru"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="set:lang:en"),
            ],
            [
                InlineKeyboardButton(
                    text="🔔 Bildirish: Yoq", callback_data="set:notif:off"
                ),
                InlineKeyboardButton(
                    text="🔔 Bildirish: Yoqish", callback_data="set:notif:on"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⏰ Eslatma vaqti", callback_data="set:reminder"
                )
            ],
        ]
    )

    await message.answer(
        f"⚙️ <b>Sozlamalar</b>\n\n" f"Til: {lang_display}\n" "Bildirish: Yoqilgan\n",
        reply_markup=kb,
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    data = await state.get_data()
    lang = data.get("language_code", "uz")
    if current is None:
        await message.answer(t("nothing_to_cancel", lang))
        return

    await state.clear()
    await message.answer(
        t("action_cancelled", lang),
        reply_markup=main_menu_keyboard(lang),
    )


@router.message(Command("quiz"))
async def cmd_quick_quiz(message: Message, state: FSMContext) -> None:
    """Oxirgi to'plamdan tez quiz boshlash."""
    from keyboards.inline import quiz_browse_keyboard

    await message.answer(
        "Qayerdan o'ynaysiz?",
        reply_markup=quiz_browse_keyboard(),
    )
