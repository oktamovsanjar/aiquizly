"""
Quiz tahrirlash (review) handlerlari.

Oqim:
  rev:start:{quiz_id}     — tahrirlashni boshlash (REVIEW state)
  rev:nav:{q_idx}         — savollar orasida navigatsiya
  rev:etxt:{q_idx}        — savol matnini tahrirlash (REVIEW_EDITING statega o'tadi)
  rev:eans:{q_idx}        — to'g'ri javobni o'zgartirish
  rev:sans:{opt}:{q_idx}  — yangi to'g'ri javobni saqlash
  rev:del:{q_idx}         — o'chirish tasdiqlash dialogi
  rev:cdel:{q_idx}        — savolni o'chirish
  rev:done                — tahrirlashni tugatish
  rev:noop                — hech narsa qilmaslik (counter button)

FSM data (REVIEW state):
  review_quiz_id  : str   — quiz UUID
  review_qid      : str   — hozir tahrirlayotgan savol UUID (etxt/eans paytida)
  review_q_idx    : int   — hozir tahrirlayotgan savol index (REVIEW_EDITING)
"""
import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from fsm.states import QuizStates
from keyboards.inline import (
    quiz_done_with_review_keyboard,
    review_answer_keyboard,
    review_delete_confirm_keyboard,
    review_nav_keyboard,
    OPTION_LABELS,
)
from utils.api import ai_engine_client

logger = logging.getLogger(__name__)
router = Router()

_CORRECT_MARK = "✅"
_WRONG_MARK = "   "


def _format_question(q: dict, idx: int, total: int) -> str:
    """Savolni chiroyli formatda ko'rsatish."""
    options: list[str] = q.get("options", [])
    correct: list[int] = q.get("correct_indices", [0])
    correct_set = set(correct)

    lines = [
        f"📋 <b>Savol {idx + 1}/{total}</b>",
        "",
        f"<b>{q.get('question_text', '—')}</b>",
        "",
    ]
    for i, opt in enumerate(options):
        mark = _CORRECT_MARK if i in correct_set else _WRONG_MARK
        label = OPTION_LABELS[i] if i < len(OPTION_LABELS) else str(i)
        lines.append(f"{mark} {label}) {opt}")

    explanation = q.get("explanation")
    if explanation:
        lines += ["", f"💡 <i>{explanation}</i>"]

    return "\n".join(lines)


async def _fetch_question(quiz_id: str, idx: int) -> dict | None:
    """AI engine dan bitta savolni oladi (offset=idx, limit=1)."""
    try:
        questions = await ai_engine_client().get_questions(quiz_id, set_number=1)
        # get_questions set bo'yicha ishlaydigan — to'g'ridan-to'g'ri offset orqali olamiz
        resp = await ai_engine_client()._http.get(
            f"/quizzes/{quiz_id}/questions",
            params={"offset": idx, "limit": 1},
        )
        if resp.is_error:
            return None
        data = resp.json()
        qs = data.get("questions", data) if isinstance(data, dict) else data
        return qs[0] if qs else None
    except Exception as exc:
        logger.warning("_fetch_question xatosi: %s", exc)
        return None


async def _get_total(quiz_id: str) -> int:
    try:
        return await ai_engine_client().count_questions(quiz_id)
    except Exception:
        return 0


async def _show_question(
    target,
    quiz_id: str,
    q_idx: int,
    total: int,
    edit: bool = True,
) -> None:
    """Savolni target (Message yoki CallbackQuery.message) ga ko'rsatadi."""
    msg = target if isinstance(target, Message) else target.message

    q = await _fetch_question(quiz_id, q_idx)
    if q is None:
        await msg.answer("❌ Savol topilmadi.")
        return

    text = _format_question(q, q_idx, total)
    kb = review_nav_keyboard(q_idx, total)

    if edit:
        try:
            await msg.edit_text(text, reply_markup=kb)
        except Exception:
            await msg.answer(text, reply_markup=kb)
    else:
        await msg.answer(text, reply_markup=kb)


# ─── Boshlash ────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("rev:start:"))
async def cb_review_start(cb: CallbackQuery, state: FSMContext) -> None:
    quiz_id = cb.data.split(":", 2)[2]
    total = await _get_total(quiz_id)

    if total == 0:
        await cb.answer("Savollar topilmadi", show_alert=True)
        return

    await state.set_state(QuizStates.REVIEW)
    await state.update_data(review_quiz_id=quiz_id)
    await cb.answer()
    await _show_question(cb, quiz_id, 0, total)


# ─── Navigatsiya ─────────────────────────────────────────────────────────────

@router.callback_query(StateFilter(QuizStates.REVIEW), F.data.startswith("rev:nav:"))
async def cb_review_nav(cb: CallbackQuery, state: FSMContext) -> None:
    q_idx = int(cb.data.split(":")[2])
    data = await state.get_data()
    quiz_id = data["review_quiz_id"]
    total = await _get_total(quiz_id)
    await cb.answer()
    await _show_question(cb, quiz_id, q_idx, total)


@router.callback_query(StateFilter(QuizStates.REVIEW), F.data == "rev:noop")
async def cb_noop(cb: CallbackQuery) -> None:
    await cb.answer()


# ─── Savol matnini tahrirlash ─────────────────────────────────────────────────

@router.callback_query(StateFilter(QuizStates.REVIEW), F.data.startswith("rev:etxt:"))
async def cb_edit_text_start(cb: CallbackQuery, state: FSMContext) -> None:
    q_idx = int(cb.data.split(":")[2])
    data = await state.get_data()
    quiz_id = data["review_quiz_id"]

    q = await _fetch_question(quiz_id, q_idx)
    if q is None:
        await cb.answer("Savol topilmadi", show_alert=True)
        return

    await state.update_data(review_qid=q["id"], review_q_idx=q_idx)
    await state.set_state(QuizStates.REVIEW_EDITING)
    await cb.answer()
    await cb.message.edit_text(
        f"✏️ <b>Savol {q_idx + 1}</b> matnini yozing:\n\n"
        f"<i>Hozirgi: {q.get('question_text', '')}</i>\n\n"
        "Yoki /cancel bosing.",
    )


@router.message(StateFilter(QuizStates.REVIEW_EDITING), F.text)
async def msg_edit_text_input(message: Message, state: FSMContext) -> None:
    if message.text == "/cancel":
        data = await state.get_data()
        await state.set_state(QuizStates.REVIEW)
        quiz_id = data["review_quiz_id"]
        q_idx = data.get("review_q_idx", 0)
        total = await _get_total(quiz_id)
        await _show_question(message, quiz_id, q_idx, total, edit=False)
        return

    data = await state.get_data()
    quiz_id = data["review_quiz_id"]
    question_id = data["review_qid"]
    q_idx = data.get("review_q_idx", 0)

    try:
        await ai_engine_client().update_question(
            quiz_id=quiz_id,
            question_id=question_id,
            question_text=message.text.strip(),
        )
        await message.answer("✅ Savol matni yangilandi.")
    except Exception as exc:
        logger.error("update_question xatosi: %s", exc)
        await message.answer("❌ Xatolik yuz berdi.")

    await state.set_state(QuizStates.REVIEW)
    total = await _get_total(quiz_id)
    await _show_question(message, quiz_id, q_idx, total, edit=False)


# ─── To'g'ri javobni o'zgartirish ────────────────────────────────────────────

@router.callback_query(StateFilter(QuizStates.REVIEW), F.data.startswith("rev:eans:"))
async def cb_edit_answer_start(cb: CallbackQuery, state: FSMContext) -> None:
    q_idx = int(cb.data.split(":")[2])
    data = await state.get_data()
    quiz_id = data["review_quiz_id"]

    q = await _fetch_question(quiz_id, q_idx)
    if q is None:
        await cb.answer("Savol topilmadi", show_alert=True)
        return

    await state.update_data(review_qid=q["id"])
    await cb.answer()
    await cb.message.edit_text(
        f"🔄 <b>Savol {q_idx + 1}</b> — to'g'ri javobni tanlang:",
        reply_markup=review_answer_keyboard(q.get("options", []), q_idx),
    )


@router.callback_query(StateFilter(QuizStates.REVIEW), F.data.startswith("rev:sans:"))
async def cb_set_answer(cb: CallbackQuery, state: FSMContext) -> None:
    parts = cb.data.split(":")
    opt_idx = int(parts[2])
    q_idx = int(parts[3])
    data = await state.get_data()
    quiz_id = data["review_quiz_id"]
    question_id = data.get("review_qid")

    if not question_id:
        await cb.answer("Xatolik: savol ID yo'q", show_alert=True)
        return

    try:
        await ai_engine_client().update_question(
            quiz_id=quiz_id,
            question_id=question_id,
            correct_indices=[opt_idx],
        )
        await cb.answer(f"✅ To'g'ri javob: {OPTION_LABELS[opt_idx] if opt_idx < len(OPTION_LABELS) else opt_idx}")
    except Exception as exc:
        logger.error("update_question (answer) xatosi: %s", exc)
        await cb.answer("❌ Xatolik yuz berdi", show_alert=True)
        return

    total = await _get_total(quiz_id)
    await _show_question(cb, quiz_id, q_idx, total)


# ─── O'chirish ────────────────────────────────────────────────────────────────

@router.callback_query(StateFilter(QuizStates.REVIEW), F.data.startswith("rev:del:"))
async def cb_delete_confirm(cb: CallbackQuery, state: FSMContext) -> None:
    q_idx = int(cb.data.split(":")[2])
    data = await state.get_data()
    quiz_id = data["review_quiz_id"]
    total = await _get_total(quiz_id)
    await cb.answer()
    await cb.message.edit_text(
        f"🗑 <b>Savol {q_idx + 1}/{total}</b> ni o'chirasizmi?\n"
        "Bu amalni qaytarib bo'lmaydi.",
        reply_markup=review_delete_confirm_keyboard(q_idx),
    )


@router.callback_query(StateFilter(QuizStates.REVIEW), F.data.startswith("rev:cdel:"))
async def cb_delete_execute(cb: CallbackQuery, state: FSMContext) -> None:
    q_idx = int(cb.data.split(":")[2])
    data = await state.get_data()
    quiz_id = data["review_quiz_id"]

    q = await _fetch_question(quiz_id, q_idx)
    if q is None:
        await cb.answer("Savol allaqachon o'chirilgan", show_alert=True)
    else:
        try:
            await ai_engine_client().delete_question(quiz_id, q["id"])
            await cb.answer("🗑 Savol o'chirildi")
        except Exception as exc:
            logger.error("delete_question xatosi: %s", exc)
            await cb.answer("❌ Xatolik yuz berdi", show_alert=True)
            return

    total = await _get_total(quiz_id)
    new_idx = min(q_idx, total - 1) if total > 0 else 0

    if total == 0:
        await state.clear()
        await cb.message.edit_text(
            "📋 Barcha savollar o'chirildi.\nYangi fayl yuklang.",
            reply_markup=None,
        )
        return

    await _show_question(cb, quiz_id, new_idx, total)


# ─── Tayyor ──────────────────────────────────────────────────────────────────

@router.callback_query(StateFilter(QuizStates.REVIEW), F.data == "rev:done")
async def cb_review_done(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    quiz_id = data.get("review_quiz_id", "")
    total = await _get_total(quiz_id)
    await state.clear()
    await cb.answer("✅ Tahrirlash tugadi")
    await cb.message.edit_text(
        f"✅ Quiz tahrirlandi!\n📊 {total} ta savol",
        reply_markup=quiz_done_with_review_keyboard(quiz_id),
    )
