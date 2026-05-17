"""
Qo'lda quiz yaratish — BOT_UX.md §6 (manual flow).

FSM oqimi:
  MANUAL_CREATE → MANUAL_CREATE_QUESTION → MANUAL_CREATE_OPTIONS → MANUAL_CREATE_CORRECT
  → (yana savol?) → MANUAL_CREATE_QUESTION | REVIEW (saqlash)
"""
import logging
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from fsm.states import QuizStates

logger = logging.getLogger(__name__)
router = Router()

MAX_OPTIONS = 10
MIN_OPTIONS = 2


def _next_question_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Yana savol qo'shish", callback_data="man:add_q"),
            InlineKeyboardButton(text="✅ Tugatish", callback_data="man:finish"),
        ],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="man:cancel")],
    ])


def _options_done_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Variantlar tayyor", callback_data="man:options_done")],
        [InlineKeyboardButton(text="❌ Bekor", callback_data="man:cancel")],
    ])


def _correct_answer_keyboard(options: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for i, opt in enumerate(options):
        label = f"{chr(65 + i)}) {opt[:30]}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"man:correct:{i}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─────────────────────── Boshlash ───────────────────────

@router.callback_query(F.data == "up:manual")
async def start_manual(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(QuizStates.MANUAL_CREATE)
    await state.update_data(manual_questions=[], manual_quiz_name="")
    await callback.message.edit_text(
        "✍️ Qo'lda quiz yaratish\n\n"
        "Quiz nomini kiriting:"
    )
    await callback.answer()


@router.message(QuizStates.MANUAL_CREATE)
async def receive_quiz_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("❌ Nom kamida 3 ta harf bo'lishi kerak.")
        return

    await state.update_data(manual_quiz_name=name)
    await state.set_state(QuizStates.MANUAL_CREATE_QUESTION)
    await message.answer(
        f"📋 <b>{name}</b>\n\n"
        "1-savolni kiriting:"
    )


# ─────────────────────── Savol matni ───────────────────────

@router.callback_query(F.data == "man:add_q")
async def add_next_question(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    q_count = len(data.get("manual_questions", [])) + 1
    await state.set_state(QuizStates.MANUAL_CREATE_QUESTION)
    await cb.message.answer(f"{q_count}-savolni kiriting:")
    await cb.answer()


@router.message(QuizStates.MANUAL_CREATE_QUESTION)
async def receive_question_text(message: Message, state: FSMContext) -> None:
    q_text = message.text.strip()
    if len(q_text) < 5:
        await message.answer("❌ Savol matni kamida 5 ta harf bo'lishi kerak.")
        return

    await state.update_data(current_question=q_text, current_options=[])
    await state.set_state(QuizStates.MANUAL_CREATE_OPTIONS)
    await message.answer(
        f"❓ <b>{q_text}</b>\n\n"
        f"Javob variantlarini yuboring (har birini alohida xabarda).\n"
        f"Kamida {MIN_OPTIONS} ta, maksimum {MAX_OPTIONS} ta variant.\n\n"
        "Tayyor bo'lgach «✅ Variantlar tayyor» bosing.",
        reply_markup=_options_done_keyboard(),
    )


# ─────────────────────── Variantlar ───────────────────────

@router.message(QuizStates.MANUAL_CREATE_OPTIONS)
async def receive_option(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    options: list = data.get("current_options", [])

    if len(options) >= MAX_OPTIONS:
        await message.answer(f"❌ Maksimum {MAX_OPTIONS} ta variant kiritildi.")
        return

    opt_text = message.text.strip()
    if not opt_text:
        return

    options.append(opt_text)
    await state.update_data(current_options=options)

    letter = chr(64 + len(options))  # A, B, C...
    await message.answer(
        f"{letter}) {opt_text} ✅\n\n"
        f"Jami: {len(options)} ta variant.\n"
        "Yana variant yuboring yoki «✅ Variantlar tayyor» bosing.",
        reply_markup=_options_done_keyboard(),
    )


@router.callback_query(F.data == "man:options_done")
async def options_done(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    options = data.get("current_options", [])

    if len(options) < MIN_OPTIONS:
        await cb.answer(
            f"Kamida {MIN_OPTIONS} ta variant kerak! Hozir {len(options)} ta.",
            show_alert=True,
        )
        return

    await state.set_state(QuizStates.MANUAL_CREATE_CORRECT)
    await cb.message.answer(
        "To'g'ri javobni tanlang:",
        reply_markup=_correct_answer_keyboard(options),
    )
    await cb.answer()


# ─────────────────────── To'g'ri javob ───────────────────────

@router.callback_query(F.data.startswith("man:correct:"))
async def receive_correct_answer(cb: CallbackQuery, state: FSMContext) -> None:
    correct_idx = int(cb.data.split(":")[2])
    data = await state.get_data()
    options = data.get("current_options", [])
    q_text = data.get("current_question", "")

    if correct_idx >= len(options):
        await cb.answer("Noto'g'ri indeks!", show_alert=True)
        return

    # Savolni ro'yxatga qo'shish
    questions: list = data.get("manual_questions", [])
    questions.append({
        "question_text": q_text,
        "options": options,
        "correct_indices": [correct_idx],
        "explanation": "",
    })
    await state.update_data(
        manual_questions=questions,
        current_question="",
        current_options=[],
    )

    letter = chr(65 + correct_idx)
    await cb.message.answer(
        f"✅ Savol qo'shildi!\n"
        f"❓ {q_text}\n"
        f"✔️ To'g'ri: {letter}) {options[correct_idx]}\n\n"
        f"Jami: <b>{len(questions)}</b> ta savol.\n\n"
        "Davom etamizmi?",
        reply_markup=_next_question_keyboard(),
    )
    await state.set_state(QuizStates.MANUAL_CREATE)
    await cb.answer()


# ─────────────────────── Tugatish ───────────────────────

@router.callback_query(F.data == "man:finish")
async def finish_manual_quiz(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    questions: list = data.get("manual_questions", [])
    quiz_name: str = data.get("manual_quiz_name", "Yangi quiz")

    if not questions:
        await cb.answer("Hech qanday savol yo'q!", show_alert=True)
        return

    await cb.message.answer(
        f"✅ <b>{quiz_name}</b>\n"
        f"📋 {len(questions)} ta savol\n\n"
        "Saqlash sozlamalari:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔒 Faqat men", callback_data="man:save:private"),
                InlineKeyboardButton(text="🌐 Ommaviy", callback_data="man:save:public"),
            ],
        ]),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("man:save:"))
async def save_manual_quiz(cb: CallbackQuery, state: FSMContext) -> None:
    visibility = cb.data.split(":")[2]
    data = await state.get_data()
    questions = data.get("manual_questions", [])
    quiz_name = data.get("manual_quiz_name", "Yangi quiz")

    from utils.api import ai_engine_client
    try:
        result = await ai_engine_client().save_manual_quiz(
            name=quiz_name,
            questions=questions,
            tags=[],
            is_public=(visibility == "public"),
            user_id=cb.from_user.id,
        )
        await cb.message.answer(
            f"✅ <b>{quiz_name}</b> saqlandi!\n"
            f"📋 {len(questions)} ta savol\n\n"
            "/quiz buyrug'i bilan boshlashingiz mumkin."
        )
    except Exception as e:
        logger.error("Manual quiz saqlash xatosi: %s", e)
        await cb.message.answer("❌ Saqlashda xato. Keyinroq urinib ko'ring.")
    finally:
        await state.clear()
    await cb.answer()


@router.callback_query(F.data == "man:cancel")
async def cancel_manual(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.answer("❌ Quiz yaratish bekor qilindi.")
    await cb.answer()
