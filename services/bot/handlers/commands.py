"""
Bot buyruqlari handlerlari — BOT_UX.md §21

/help     — Yordam
/settings — Sozlamalar
/cancel   — Bekor qilish
/quiz     — Tez quiz
"""
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from fsm.states import QuizStates
from keyboards.main_menu import main_menu_keyboard

router = Router()


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>Quiz Bot — Yordam</b>\n\n"
        "📋 <b>Buyruqlar:</b>\n"
        "/start — Botni boshlash\n"
        "/quiz — Tez quiz (oxirgi to'plamdan)\n"
        "/create — Quiz yaratish (fayl/rasm/qo'lda)\n"
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

    lang_display = {"uz": "🇺🇿 O'zbek", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}.get(lang, "🇺🇿 O'zbek")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="set:lang:uz"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set:lang:ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="set:lang:en"),
        ],
        [
            InlineKeyboardButton(text="🔔 Bildirish: Yoq", callback_data="set:notif:off"),
            InlineKeyboardButton(text="🔔 Bildirish: Yoqish", callback_data="set:notif:on"),
        ],
        [InlineKeyboardButton(text="⏰ Eslatma vaqti", callback_data="set:reminder")],
    ])

    await message.answer(
        f"⚙️ <b>Sozlamalar</b>\n\n"
        f"Til: {lang_display}\n"
        "Bildirish: Yoqilgan\n",
        reply_markup=kb,
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current is None:
        await message.answer("Bekor qilish uchun hech narsa yo'q.")
        return

    await state.clear()
    await message.answer(
        "✅ Amal bekor qilindi.",
        reply_markup=main_menu_keyboard("uz"),
    )


@router.message(Command("quiz"))
async def cmd_quick_quiz(message: Message, state: FSMContext) -> None:
    """Oxirgi to'plamdan tez quiz boshlash."""
    from keyboards.inline import quiz_browse_keyboard
    await message.answer(
        "Qayerdan o'ynaysiz?",
        reply_markup=quiz_browse_keyboard(),
    )
