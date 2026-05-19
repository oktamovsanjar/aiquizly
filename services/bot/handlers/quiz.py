"""Quiz oqimi — ko'rish, tanlash, o'ynash, to'xtatish, natijalar."""

import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import (
    CallbackQuery,
    Message,
    PollAnswer,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from fsm.states import QuizStates
from aiogram.filters import StateFilter

from keyboards.inline import (
    quiz_browse_keyboard,
    quiz_list_keyboard,
    my_quiz_list_keyboard,
    quiz_manage_keyboard,
    quiz_delete_confirm_keyboard,
    set_select_keyboard,
    time_select_keyboard,
    quiz_start_keyboard,
    stop_quiz_keyboard,
    pause_quiz_keyboard,
    quiz_result_keyboard,
    retry_result_keyboard,
)
from utils.api import ai_engine_client, game_client
from utils.i18n import t

logger = logging.getLogger(__name__)

# Auto-pause: 2 ta ketma-ket skip bo'lsa pauza
AUTO_PAUSE_SKIP_COUNT = 2

router = Router()

# Har bir poll uchun auto-advance timer: {user_id:poll_id -> Task}
_poll_timers: dict[str, asyncio.Task] = {}


def _timer_key(user_id: int, poll_id: str) -> str:
    return f"{user_id}:{poll_id}"


# ─────────────────────────── Boshlash menyusi ───────────────────────────


@router.message(F.text.in_({"▶️ Boshlash", "▶️ Start", "▶️ Начать"}))
@router.message(Command("quiz"))
async def quiz_start_menu(message: Message, state: FSMContext) -> None:
    await state.set_state(QuizStates.BROWSING_MY_QUIZZES)
    data = await state.get_data()
    lang = data.get("language_code", "uz")
    await message.answer(
        t("quiz_select_mode", lang),
        reply_markup=quiz_browse_keyboard(),
    )


@router.callback_query(F.data == "up:menu")
async def upload_menu(cb: CallbackQuery, state: FSMContext) -> None:
    """Fayl yuklash menyusiga o'tish (inline tugma orqali)."""
    from keyboards.inline import upload_menu_keyboard

    data = await state.get_data()
    lang = data.get("language_code", "uz")
    await state.set_state(QuizStates.FILE_UPLOAD)
    await cb.message.edit_text(
        t("upload_select_method", lang),
        reply_markup=upload_menu_keyboard(),
    )
    await cb.answer()


@router.callback_query(F.data == "qb:menu")
async def back_to_menu(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language_code", "uz")
    await state.clear()
    await cb.message.edit_text(
        t("quiz_select_mode", lang),
        reply_markup=quiz_browse_keyboard(),
    )
    await cb.answer()


# ─────────────────────────── Mening quizlarim ───────────────────────────


@router.callback_query(F.data == "qb:my")
async def browse_my_quizzes(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(QuizStates.BROWSING_MY_QUIZZES)
    user_id = str(cb.from_user.id)
    try:
        data = await ai_engine_client().get_quizzes(user_id=int(user_id))
        quizzes = data.get("quizzes", []) if isinstance(data, dict) else (data or [])
    except Exception:
        quizzes = []

    if not quizzes:
        await cb.message.edit_text(
            "📂 Sizda hali quizlar yo'q.\n\nFayl yuklash orqali yarating!",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📤 Quiz yaratish", callback_data="up:menu"
                        )
                    ],
                    [InlineKeyboardButton(text="🏠 Menyu", callback_data="qb:menu")],
                ]
            ),
        )
        await cb.answer()
        return

    await cb.message.edit_text(
        "📂 Sizning to'plamlaringiz:",
        reply_markup=my_quiz_list_keyboard(quizzes),
    )
    await cb.answer()


# ─────────────────────────── Quiz boshqaruvi (manage) ───────────────────────────


async def _bot_username(bot) -> str:
    try:
        me = await bot.get_me()
        return me.username or "aiquizaibot"
    except Exception:
        return "aiquizaibot"


@router.callback_query(F.data.startswith("qb:manage:"))
async def quiz_manage_menu(cb: CallbackQuery, state: FSMContext) -> None:
    quiz_id = cb.data.split(":", 2)[2]
    try:
        quiz = await ai_engine_client().get_quiz(quiz_id)
    except Exception:
        await cb.answer("Quiz topilmadi", show_alert=True)
        return

    is_public = quiz.get("visibility") == "public"
    vis_icon = "🌐" if is_public else "🔒"
    title = quiz.get("title", "Quiz")
    total = quiz.get("total_questions", 0)

    await state.update_data(manage_quiz_id=quiz_id)
    await cb.message.edit_text(
        f"⚙️ <b>{title}</b>\n"
        f"📊 {total} ta savol  {vis_icon} {'Ochiq' if is_public else 'Yopiq'}",
        reply_markup=quiz_manage_keyboard(
            quiz_id, is_public, await _bot_username(cb.bot)
        ),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("qb:vis:"))
async def quiz_toggle_visibility(cb: CallbackQuery) -> None:
    quiz_id = cb.data.split(":", 2)[2]
    try:
        quiz = await ai_engine_client().get_quiz(quiz_id)
        is_public = quiz.get("visibility") == "public"
        updated = await ai_engine_client().update_quiz(quiz_id, is_public=not is_public)
        new_public = updated.get("visibility") == "public"
        await cb.answer(f"✅ {'Ochiq' if new_public else 'Yopiq'} qilindi")
    except Exception:
        await cb.answer("❌ Xatolik yuz berdi", show_alert=True)
        return

    title = quiz.get("title", "Quiz")
    total = quiz.get("total_questions", 0)
    vis_icon = "🌐" if new_public else "🔒"
    await cb.message.edit_text(
        f"⚙️ <b>{title}</b>\n"
        f"📊 {total} ta savol  {vis_icon} {'Ochiq' if new_public else 'Yopiq'}",
        reply_markup=quiz_manage_keyboard(
            quiz_id, new_public, await _bot_username(cb.bot)
        ),
    )


@router.callback_query(F.data.startswith("qb:del_quiz:"))
async def quiz_delete_confirm(cb: CallbackQuery) -> None:
    quiz_id = cb.data.split(":", 2)[2]
    try:
        quiz = await ai_engine_client().get_quiz(quiz_id)
    except Exception:
        await cb.answer("Quiz topilmadi", show_alert=True)
        return

    await cb.answer()
    await cb.message.edit_text(
        f"🗑 <b>{quiz.get('title', 'Quiz')}</b> ni o'chirasizmi?\n"
        "Bu amalni qaytarib bo'lmaydi.",
        reply_markup=quiz_delete_confirm_keyboard(quiz_id),
    )


@router.callback_query(F.data.startswith("qb:cdel_quiz:"))
async def quiz_delete_execute(cb: CallbackQuery) -> None:
    quiz_id = cb.data.split(":", 2)[2]
    try:
        await ai_engine_client().delete_quiz(quiz_id)
        await cb.answer("🗑 Quiz o'chirildi")
    except Exception:
        await cb.answer("❌ Xatolik yuz berdi", show_alert=True)
        return

    # Ro'yxatga qaytish
    user_id = cb.from_user.id
    try:
        data = await ai_engine_client().get_quizzes(user_id=user_id)
        quizzes = data.get("quizzes", []) if isinstance(data, dict) else (data or [])
    except Exception:
        quizzes = []

    if not quizzes:
        await cb.message.edit_text(
            "📂 Sizda hali quizlar yo'q.\n\nFayl yuklash orqali yarating!",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📤 Quiz yaratish", callback_data="up:menu"
                        )
                    ],
                    [InlineKeyboardButton(text="🏠 Menyu", callback_data="qb:menu")],
                ]
            ),
        )
    else:
        await cb.message.edit_text(
            "📂 Sizning to'plamlaringiz:",
            reply_markup=my_quiz_list_keyboard(quizzes),
        )


@router.callback_query(F.data.startswith("qb:rename:"))
async def quiz_rename_start(cb: CallbackQuery, state: FSMContext) -> None:
    quiz_id = cb.data.split(":", 2)[2]
    try:
        quiz = await ai_engine_client().get_quiz(quiz_id)
    except Exception:
        await cb.answer("Quiz topilmadi", show_alert=True)
        return

    await state.update_data(manage_quiz_id=quiz_id)
    await state.set_state(QuizStates.QUIZ_RENAME)
    await cb.answer()
    await cb.message.edit_text(
        f"✏️ <b>{quiz.get('title', 'Quiz')}</b> — yangi nomini yozing:\n\n"
        "Yoki /cancel bosing."
    )


@router.message(StateFilter(QuizStates.QUIZ_RENAME), F.text)
async def quiz_rename_input(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    quiz_id = data.get("manage_quiz_id")

    if message.text == "/cancel" or not quiz_id:
        await state.clear()
        await message.answer("❌ Bekor qilindi.")
        return

    new_title = message.text.strip()[:100]
    try:
        updated = await ai_engine_client().update_quiz(quiz_id, title=new_title)
        await message.answer(
            f"✅ Nom o'zgartirildi: <b>{updated.get('title', new_title)}</b>"
        )
    except Exception:
        await message.answer("❌ Xatolik yuz berdi.")
        await state.clear()
        return

    await state.clear()
    # Manage menyusiga qaytish
    try:
        quiz = await ai_engine_client().get_quiz(quiz_id)
        is_public = quiz.get("visibility") == "public"
        total = quiz.get("total_questions", 0)
        vis_icon = "🌐" if is_public else "🔒"
        await message.answer(
            f"⚙️ <b>{quiz.get('title', new_title)}</b>\n"
            f"📊 {total} ta savol  {vis_icon} {'Ochiq' if is_public else 'Yopiq'}",
            reply_markup=quiz_manage_keyboard(
                quiz_id, is_public, await _bot_username(message.bot)
            ),
        )
    except Exception:
        pass


# ─────────────────────────── Obunalarim ───────────────────────────


@router.callback_query(F.data == "qb:subs")
async def browse_subscriptions(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(QuizStates.BROWSING_SUBSCRIPTIONS)
    from db import AsyncSessionLocal
    from db.models import QuizGroupSubscriber, QuizGroup, User
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(QuizGroup)
            .join(
                QuizGroupSubscriber, QuizGroupSubscriber.quiz_group_id == QuizGroup.id
            )
            .join(User, User.id == QuizGroupSubscriber.user_id)
            .where(User.telegram_id == cb.from_user.id)
            .where(QuizGroup.is_active)
        )
        groups = result.scalars().all()

    if not groups:
        await cb.message.edit_text(
            "📌 Siz hali hech qaysi quiz guruhiga obuna bo'lmagansiz.\n\n"
            "Ommaviy quizlarda guruhlarni topishingiz mumkin.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🌐 Ommaviy quizlar", callback_data="qb:public"
                        )
                    ],
                    [InlineKeyboardButton(text="🏠 Menyu", callback_data="qb:menu")],
                ]
            ),
        )
        await cb.answer()
        return

    from keyboards.inline import quiz_group_list_keyboard

    groups_data = [
        {"id": str(g.id), "name": g.name, "subscriber_count": g.subscriber_count}
        for g in groups
    ]
    await cb.message.edit_text(
        "📌 Sizning obunalaringiz:",
        reply_markup=quiz_group_list_keyboard(groups_data),
    )
    await cb.answer()


# ─────────────────────────── Ommaviy / Trend ───────────────────────────


@router.callback_query(F.data.in_({"qb:public", "qb:trending", "qb:random"}))
async def browse_public_quizzes(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(QuizStates.BROWSING_PUBLIC)
    mode = cb.data.split(":")[1]
    try:
        if mode == "trending":
            data = await ai_engine_client().get_quizzes(tag=None, public=True)
        elif mode == "random":
            import random

            data = await ai_engine_client().get_quizzes(public=True, page_size=20)
            quizzes_all = (
                data.get("quizzes", []) if isinstance(data, dict) else (data or [])
            )
            if quizzes_all:
                random.shuffle(quizzes_all)
                quizzes_all = quizzes_all[:5]
            data = {"quizzes": quizzes_all}
        else:
            data = await ai_engine_client().get_quizzes(public=True)
        quizzes = data.get("quizzes", []) if isinstance(data, dict) else (data or [])
    except Exception:
        quizzes = []

    if not quizzes:
        await cb.message.edit_text(
            "🌐 Hozircha ommaviy quizlar yo'q.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🏠 Menyu", callback_data="qb:menu")]
                ]
            ),
        )
        await cb.answer()
        return

    await cb.message.edit_text(
        "🌐 Ommaviy quizlar:",
        reply_markup=quiz_list_keyboard(quizzes),
    )
    await cb.answer()


# ─────────────────────────── Quiz tanlash → Set tanlash ───────────────────────────


@router.callback_query(F.data.startswith("qb:play:"))
async def play_quiz_direct(cb: CallbackQuery, state: FSMContext) -> None:
    """Upload tugagandan keyin bevosita o'ynash uchun shortcut."""
    quiz_id = cb.data.split(":")[2]
    await _show_set_select(cb, state, quiz_id)


async def _show_set_select(cb: CallbackQuery, state: FSMContext, quiz_id: str) -> None:
    """Set tanlash ekranini ko'rsatish — ichki yordamchi."""
    try:
        quiz = await ai_engine_client().get_quiz(quiz_id)
    except Exception:
        await cb.answer("Quiz topilmadi", show_alert=True)
        return

    total_q = quiz.get("total_questions", 0)
    set_size = 20
    num_sets = max(1, (total_q + set_size - 1) // set_size)
    sets = [
        {"set_number": i + 1, "question_count": min(set_size, total_q - i * set_size)}
        for i in range(num_sets)
    ]

    await state.update_data(quiz_id=quiz_id, quiz_title=quiz.get("title", "Quiz"))
    await cb.message.edit_text(
        f"📋 <b>{quiz.get('title', 'Quiz')}</b>\n"
        f"📏 {total_q} savol | {num_sets} set\n\n"
        "Set tanlang:",
        reply_markup=set_select_keyboard(sets, quiz_id),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("qb:quiz:"))
async def select_quiz(cb: CallbackQuery, state: FSMContext) -> None:
    quiz_id = cb.data.split(":")[2]
    await _show_set_select(cb, state, quiz_id)


# ─────────────────────────── Navigatsiya / Orqaga ───────────────────────────


@router.callback_query(F.data == "qb:back")
async def back_to_quiz_list(cb: CallbackQuery, state: FSMContext) -> None:
    """Set tanlash ekranidan quiz ro'yxatiga qaytish."""
    browsing_state = await state.get_state()
    if browsing_state == QuizStates.BROWSING_PUBLIC.state:
        await browse_public_quizzes(cb, state)
    else:
        await browse_my_quizzes(cb, state)


@router.callback_query(F.data.startswith("qp:back_set:"))
async def back_to_set_select(cb: CallbackQuery, state: FSMContext) -> None:
    """Vaqt tanlashdan set tanlashga qaytish."""
    quiz_id = cb.data.split(":")[2]
    await _show_set_select(cb, state, quiz_id)


@router.callback_query(F.data.startswith("qp:change_time:"))
async def change_time(cb: CallbackQuery, state: FSMContext) -> None:
    """Start ekranidan vaqtni o'zgartirish."""
    parts = cb.data.split(":")
    quiz_id = parts[2]
    set_number = int(parts[3])
    await state.update_data(quiz_id=quiz_id, set_number=set_number)
    await state.set_state(QuizStates.QUIZ_SETUP)
    data = await state.get_data()
    lang = data.get("language_code", "uz")
    await cb.message.edit_text(
        t("quiz_select_time", lang),
        reply_markup=time_select_keyboard(quiz_id, set_number),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("qb:page:"))
async def quiz_list_page(cb: CallbackQuery, state: FSMContext) -> None:
    """Quiz ro'yxatida sahifalar."""
    page = int(cb.data.split(":")[2])
    data, browsing_state = await asyncio.gather(state.get_data(), state.get_state())
    user_id = cb.from_user.id
    try:
        if browsing_state == QuizStates.BROWSING_MY_QUIZZES.state:
            resp = await ai_engine_client().get_quizzes(user_id=user_id, page=page)
        else:
            resp = await ai_engine_client().get_quizzes(public=True, page=page)
        quizzes = resp.get("quizzes", []) if isinstance(resp, dict) else (resp or [])
        total = len(quizzes) + (page - 1) * 10
        has_next = page * 10 < total
    except Exception:
        quizzes, has_next = [], False
    if not quizzes:
        await cb.answer("Boshqa sahifa yo'q", show_alert=True)
        return
    await cb.message.edit_reply_markup(
        reply_markup=quiz_list_keyboard(quizzes, page=page, has_next=has_next)
    )
    await cb.answer()


# ─────────────────────────── Set → Vaqt tanlash ───────────────────────────


@router.callback_query(F.data.startswith("qp:set:"))
async def select_set(cb: CallbackQuery, state: FSMContext) -> None:
    parts = cb.data.split(":")
    quiz_id = parts[2]
    set_number = int(parts[3])
    # 5-qism bo'lsa — vaqt ham berilgan, to'g'ridan boshlash
    if len(parts) >= 5:
        time_sec = int(parts[4])
        await _start_quiz_from(cb, state, quiz_id, set_number, time_sec)
        return

    data = await state.get_data()
    lang = data.get("language_code", "uz")
    await asyncio.gather(
        state.update_data(quiz_id=quiz_id, set_number=set_number, time_sec=30),
        state.set_state(QuizStates.QUIZ_SETUP),
    )

    await cb.message.edit_text(
        t("quiz_select_time", lang),
        reply_markup=time_select_keyboard(quiz_id, set_number),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("qp:time:"))
async def select_time(cb: CallbackQuery, state: FSMContext) -> None:
    parts = cb.data.split(":")
    quiz_id = parts[2]
    set_number = int(parts[3])
    time_sec = int(parts[4])

    data = await state.get_data()
    quiz_title = data.get("quiz_title", "Quiz")
    shuffle_q = data.get("shuffle_questions", True)
    shuffle_o = data.get("shuffle_options", True)

    await state.update_data(time_sec=time_sec)

    await cb.message.edit_text(
        f"📋 <b>{quiz_title}</b> — Set {set_number}\n"
        f"⏱ Har savol: {time_sec} soniya\n\n"
        "Tayyormisiz?",
        reply_markup=quiz_start_keyboard(
            quiz_id, set_number, time_sec, shuffle_q, shuffle_o
        ),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("qp:toggle_sq:"))
async def toggle_shuffle_questions(cb: CallbackQuery, state: FSMContext) -> None:
    parts = cb.data.split(":")
    quiz_id, set_number, time_sec = parts[2], int(parts[3]), int(parts[4])
    data = await state.get_data()
    shuffle_q = not data.get("shuffle_questions", True)
    shuffle_o = data.get("shuffle_options", True)
    await state.update_data(shuffle_questions=shuffle_q)
    await cb.message.edit_reply_markup(
        reply_markup=quiz_start_keyboard(
            quiz_id, set_number, time_sec, shuffle_q, shuffle_o
        )
    )
    await cb.answer()


@router.callback_query(F.data.startswith("qp:toggle_so:"))
async def toggle_shuffle_options(cb: CallbackQuery, state: FSMContext) -> None:
    parts = cb.data.split(":")
    quiz_id, set_number, time_sec = parts[2], int(parts[3]), int(parts[4])
    data = await state.get_data()
    shuffle_q = data.get("shuffle_questions", True)
    shuffle_o = not data.get("shuffle_options", True)
    await state.update_data(shuffle_options=shuffle_o)
    await cb.message.edit_reply_markup(
        reply_markup=quiz_start_keyboard(
            quiz_id, set_number, time_sec, shuffle_q, shuffle_o
        )
    )
    await cb.answer()


# ─────────────────────────── Quiz boshlash ───────────────────────────


@router.callback_query(F.data.startswith("qp:start:"))
async def start_quiz(cb: CallbackQuery, state: FSMContext) -> None:
    parts = cb.data.split(":")
    await _start_quiz_from(cb, state, parts[2], int(parts[3]), int(parts[4]))


async def _start_quiz_from(cb: CallbackQuery, state: FSMContext, quiz_id: str, set_number: int, time_sec: int) -> None:
    """Quiz boshlaydigan asosiy logika."""
    await state.set_state(QuizStates.QUIZ_PLAYING)
    await state.update_data(
        quiz_id=quiz_id,
        set_number=set_number,
        time_sec=time_sec,
        current_q_index=0,
        skip_count=0,
        correct=0,
        wrong=0,
        skipped=0,
        wrong_question_ids=[],
        current_poll_id=None,
        _finishing=False,
    )

    questions_result, game_result = await asyncio.gather(
        ai_engine_client().get_questions(quiz_id, set_number),
        game_client().start_game(
            user_id=cb.from_user.id,
            quiz_id=quiz_id,
            set_number=set_number,
            time_per_question=time_sec,
        ),
        return_exceptions=True,
    )

    if isinstance(questions_result, Exception):
        await cb.message.edit_text(
            "❌ Savollarni yuklab bo'lmadi. Qaytadan urinib ko'ring."
        )
        await state.clear()
        await cb.answer()
        return

    questions = list(questions_result)
    if not questions:
        await cb.message.edit_text("❌ Bu setda savollar topilmadi.")
        await state.clear()
        await cb.answer()
        return

    fsm_data = await state.get_data()
    if fsm_data.get("shuffle_questions", True):
        import random

        random.shuffle(questions)

    await state.update_data(questions=questions, total=len(questions))

    if isinstance(game_result, dict):
        await state.update_data(game_id=game_result.get("game_id"))

    await cb.message.delete()
    await cb.answer()

    await _send_next_question(cb.message.chat.id, cb.from_user.id, state, cb.bot)


# ─────────────────────────── Savol yuborish + auto-advance timer ───────────────────────────


async def _send_next_question(
    chat_id: int, user_id: int, state: FSMContext, bot
) -> None:
    """Keyingi savolni yuboradi va vaqt tugaganda auto-advance timerni o'rnatadi."""
    data, current_state = await asyncio.gather(state.get_data(), state.get_state())

    # Agar quiz to'xtatilgan / pauzada bo'lsa — savol yuborma
    if current_state not in (QuizStates.QUIZ_PLAYING.state, None):
        return

    questions = data.get("questions", [])
    idx = data.get("current_q_index", 0)
    total = data.get("total", len(questions))
    time_sec = data.get("time_sec", 30)

    if idx >= total:
        await _show_results(chat_id, user_id, state, bot)
        return

    q = questions[idx]
    options = list(q.get("options", []))
    correct_idx = (
        q.get("correct_indices", [0])[0]
        if q.get("correct_indices")
        else q.get("correct_index", 0)
    )

    # Options shuffle: indekslarni kuzatib boramiz
    if data.get("shuffle_options", True) and len(options) > 1:
        import random

        indexed = list(enumerate(options))
        random.shuffle(indexed)
        # orig_positions[i] = original index of the option now at position i
        orig_positions = [orig_i for orig_i, _ in indexed]
        options = [opt for _, opt in indexed]
        # Correct option endi qaysi pozitsiyada?
        correct_idx = orig_positions.index(correct_idx)

    # Savol matnini qisqartirish — Telegram max 300 belgi
    q_text = q.get("question_text", q.get("question", ""))
    poll_question = f"({idx + 1}/{total}) {q_text}"
    if len(poll_question) > 300:
        poll_question = poll_question[:297] + "..."

    # Variantlarni qisqartirish — Telegram max 100 belgi
    options = [o[:100] if len(o) > 100 else o for o in options]

    msg = await bot.send_poll(
        chat_id=chat_id,
        question=poll_question,
        options=options,
        type="quiz",
        correct_option_id=correct_idx,
        explanation=q.get("explanation") or None,
        open_period=time_sec,
        is_anonymous=False,
    )

    poll_id = msg.poll.id
    # current_poll_correct_idx: Telegram ga yuborilgan haqiqiy to'g'ri indeks
    # (shuffle bo'lmasa ham saqlaymiz — on_poll_answer shu qiymatni ishlatadi)
    # last_poll_id: hech qachon tozalanmaydi — race condition fix uchun
    await state.update_data(
        current_poll_id=poll_id,
        last_poll_id=poll_id,
        current_poll_msg_id=msg.message_id,
        current_q_index=idx + 1,
        current_poll_correct_idx=correct_idx,
    )

    # Avvalgi timerni bekor qil
    old_key = _timer_key(user_id, data.get("current_poll_id", ""))
    old_task = _poll_timers.pop(old_key, None)
    if old_task and not old_task.done():
        old_task.cancel()

    # Vaqt tugagach auto-advance
    key = _timer_key(user_id, poll_id)
    task = asyncio.create_task(
        _auto_advance(bot, chat_id, user_id, state, poll_id, time_sec, key)
    )
    _poll_timers[key] = task


async def _auto_advance(
    bot,
    chat_id: int,
    user_id: int,
    state: FSMContext,
    poll_id: str,
    time_sec: int,
    task_key: str,
) -> None:
    """Vaqt tugagach (time_sec + 1.5s), user javob bermagan bo'lsa keyingi savolga o'tish."""
    await asyncio.sleep(time_sec + 1.5)
    _poll_timers.pop(task_key, None)

    data, current_state = await asyncio.gather(state.get_data(), state.get_state())
    if not data.get("questions"):
        return

    # Agar allaqachon boshqa savol yuborilgan bo'lsa — bu timer eski
    if data.get("current_poll_id") != poll_id:
        return

    if current_state == QuizStates.PAUSED.state:
        return

    # Bu savolga javob berilmadi → skip
    idx = data.get("current_q_index", 1) - 1
    skip_count = data.get("skip_count", 0) + 1
    skipped = data.get("skipped", 0) + 1
    await state.update_data(
        skipped=skipped, skip_count=skip_count, current_poll_id=None
    )

    # Game servisga skip yuborish
    game_id = data.get("game_id")
    if game_id and idx >= 0:
        try:
            await game_client().submit_answer(
                game_id=game_id,
                question_index=idx,
                chosen_option=None,
                time_taken_ms=time_sec * 1000,
            )
        except Exception:
            pass

    if skip_count >= AUTO_PAUSE_SKIP_COUNT:
        await state.set_state(QuizStates.PAUSED)
        await state.update_data(skip_count=0)
        fsm_data = await state.get_data()
        lang = fsm_data.get("language_code", "uz")
        pause_msg = await bot.send_message(
            chat_id,
            t("quiz_paused", lang),
            reply_markup=pause_quiz_keyboard(),
        )
        # Pauza xabari ID ni saqlaymiz — agar user kech javob bersa o'chiramiz
        await state.update_data(pause_msg_id=pause_msg.message_id)
        return

    await _send_next_question(chat_id, user_id, state, bot)


# ─────────────────────────── Poll javobi ───────────────────────────


@router.poll_answer()
async def on_poll_answer(poll_answer: PollAnswer, state: FSMContext, bot: Bot) -> None:
    """Foydalanuvchi poll ga javob berganda."""
    # Guruhda voter_chat tufayli FSMContext noto'g'ri chat_id bilan keladi.
    # User state har doim user_id = chat_id kalit bilan saqlanadi — qo'lda olamiz.
    user_id = poll_answer.user.id
    real_state = FSMContext(
        storage=state.storage,
        key=StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id),
    )
    data = await real_state.get_data()
    if not data.get("questions"):
        return
    state = real_state

    current_poll_id = data.get("current_poll_id")
    last_poll_id = data.get("last_poll_id")

    if poll_answer.poll_id == current_poll_id:
        # Oddiy holat: timer hali ishlamagan, javob o'z vaqtida keldi
        key = _timer_key(poll_answer.user.id, poll_answer.poll_id)
        task = _poll_timers.pop(key, None)
        if task and not task.done():
            task.cancel()
        await state.update_data(current_poll_id=None, current_poll_correct_idx=None)

    elif poll_answer.poll_id == last_poll_id and current_poll_id is None:
        # Race condition: timer on_poll_answer dan oldin ishladi.
        # Agar _auto_advance keyingi savolni yuborgan bo'lsa, last_poll_id yangilangan
        # bo'ladi → bu shart bajarilmaydi. Demak faqat PAUSED yoki skip holati.
        # Noto'g'ri hisoblangan skipni bekor qilamiz
        await state.update_data(
            skip_count=max(0, data.get("skip_count", 0) - 1),
            skipped=max(0, data.get("skipped", 0) - 1),
            current_poll_id=None,
            current_poll_correct_idx=None,
        )
        # Agar pauza bo'lgan bo'lsa, qayta PLAYING ga qaytaramiz
        current_state = await state.get_state()
        if current_state == QuizStates.PAUSED.state:
            await state.set_state(QuizStates.QUIZ_PLAYING)
            # Pauza xabarini o'chiramiz
            pause_msg_id = data.get("pause_msg_id")
            if pause_msg_id:
                try:
                    await bot.delete_message(poll_answer.user.id, pause_msg_id)
                except Exception:
                    pass
                await state.update_data(pause_msg_id=None)
    else:
        # Eski yoki aloqasiz poll — e'tiborsiz
        return

    idx = data.get("current_q_index", 1) - 1
    questions = data.get("questions", [])
    if idx < 0 or idx >= len(questions):
        return

    selected = poll_answer.option_ids

    # Telegram ga yuborilgan haqiqiy to'g'ri indeksni ishlatamiz.
    # Bu shuffle bo'lsa yangi pozitsiyani, bo'lmasa original indeksni ko'rsatadi.
    # late_answer holatida current_poll_correct_idx tozalangan — data dan o'qiymiz
    correct_idx = data.get("current_poll_correct_idx")
    if correct_idx is None:
        q = questions[idx]
        correct_idx = (
            q.get("correct_indices", [0])[0]
            if q.get("correct_indices")
            else q.get("correct_index", 0)
        )

    is_correct = bool(selected) and len(selected) == 1 and selected[0] == correct_idx
    is_wrong = bool(selected) and not is_correct

    if is_correct:
        await state.update_data(
            correct=data.get("correct", 0) + 1,
            skip_count=0,
        )
    elif is_wrong:
        wrong_q_ids = data.get("wrong_question_ids", [])
        wrong_q_ids.append(idx)
        await state.update_data(
            wrong=data.get("wrong", 0) + 1,
            skip_count=0,
            wrong_question_ids=wrong_q_ids,
        )
    # selected bo'sh holat (timer allaqachon _auto_advance da ishlagan) — bu yerga yetmaydi

    # Game servisga javobni yuborish (XP hisoblash uchun)
    game_id = data.get("game_id")
    if game_id:
        try:
            await game_client().submit_answer(
                game_id=game_id,
                question_index=idx,
                chosen_option=selected[0] if selected else None,
                time_taken_ms=data.get("time_sec", 30) * 1000,
            )
        except Exception:
            pass

    # late_answer holatida ham oddiy holat kabi keyingi savolni yuboramiz
    await _send_next_question(
        poll_answer.user.id, poll_answer.user.id, state, bot
    )  # noqa: E501


# ─────────────────────────── To'xtatish / Pauza ───────────────────────────


@router.message(Command("stop"))
@router.callback_query(F.data == "qp:stop")
async def stop_quiz(event, state: FSMContext) -> None:
    data = await state.get_data()
    current = data.get("current_q_index", 0)
    total = data.get("total", 0)

    msg = event.message if isinstance(event, CallbackQuery) else event
    await msg.answer(
        f"⏹ Quizni to'xtatmoqchimisiz?\n"
        f"Hozircha {current}/{total} savol yechdingiz.",
        reply_markup=stop_quiz_keyboard(current, total),
    )
    if isinstance(event, CallbackQuery):
        await event.answer()


@router.callback_query(F.data == "qp:stop_result")
async def stop_and_show_result(cb: CallbackQuery, state: FSMContext) -> None:
    await _show_results(
        cb.message.chat.id, cb.from_user.id, state, cb.bot, message=cb.message
    )
    await cb.answer()


@router.callback_query(F.data == "qp:pause_finish")
async def pause_and_finish(cb: CallbackQuery, state: FSMContext) -> None:
    """Pauza holatidan natijalarni ko'rsatish."""
    await _show_results(
        cb.message.chat.id, cb.from_user.id, state, cb.bot, message=cb.message
    )
    await cb.answer()


@router.callback_query(F.data == "qp:continue")
async def continue_quiz(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(QuizStates.QUIZ_PLAYING)
    chat_id = cb.message.chat.id
    user_id = cb.from_user.id
    await cb.message.delete()
    await cb.answer()
    await _send_next_question(chat_id, user_id, state, cb.bot)


# ─────────────────────────── Natijalar ───────────────────────────


async def _show_results(
    chat_id: int, user_id: int, state: FSMContext, bot, message=None
) -> None:
    data = await state.get_data()

    # Guard: ikki marta chaqirilishni oldini olish
    if data.get("_finishing"):
        logger.warning("_show_results: _finishing=True, skip. user=%s", user_id)
        return
    await state.update_data(_finishing=True)
    logger.info("_show_results: user=%s correct=%s wrong=%s total=%s",
                user_id, data.get("correct"), data.get("wrong"), data.get("total"))

    correct = data.get("correct", 0)
    wrong = data.get("wrong", 0)
    skipped = data.get("skipped", 0)
    total = data.get("total", correct + wrong + skipped)
    quiz_id = data.get("quiz_id", "")
    set_number = data.get("set_number", 1)
    time_sec = data.get("time_sec", 30)
    game_id = data.get("game_id")
    lang = data.get("language_code", "uz")

    # Joriy poll timerni to'xtat
    current_poll_id = data.get("current_poll_id")
    if current_poll_id:
        key = _timer_key(user_id, current_poll_id)
        task = _poll_timers.pop(key, None)
        if task and not task.done():
            task.cancel()

    score = int((correct / total * 1000)) if total > 0 else 0
    perfect = correct == total and total > 0
    header = "💯 Mukammal!" if perfect else t("quiz_completed", lang)

    xp_earned = 0
    new_achievements = []
    if game_id:
        try:
            from utils.api import _cache_invalidate

            result = await game_client().finish_game(game_id, status="completed")
            xp_earned = result.get("xp_earned", 0)
            new_achievements = result.get("new_achievements", [])
            # Stats/rank cache ni tozalaymiz — profil yangi XP ni ko'rsin
            _cache_invalidate(f"stats:{user_id}")
            _cache_invalidate(f"rank:{user_id}")
        except Exception:
            pass

    text = (
        f"{header}\n\n"
        f"✅ To'g'ri: {correct}/{total}\n"
        f"❌ Noto'g'ri: {wrong}/{total}\n"
        f"⏭ Javobsiz: {skipped}/{total}\n\n"
        f"🏆 Ball: {score} / 1000\n"
    )
    if xp_earned:
        text += f"\n+{xp_earned} XP yutdingiz!"
    if new_achievements:
        text += f"\n🏅 Yangi yutuq: {', '.join(new_achievements)}"

    next_set = (
        set_number + 1 if (correct + wrong + skipped) >= total and total > 0 else None
    )

    try:
        me = await bot.get_me()
        bot_username = me.username or "aiquizaibot"
    except Exception:
        bot_username = "aiquizaibot"

    kb = quiz_result_keyboard(
        quiz_id=quiz_id,
        set_number=set_number,
        next_set=next_set,
        has_wrong=wrong > 0,
        time_sec=time_sec,
        bot_username=bot_username,
    )

    if message:
        await message.answer(text, reply_markup=kb)
    else:
        await bot.send_message(chat_id, text, reply_markup=kb)

    # State ni IDLE ga qaytaramiz lekin data ni SAQLAYMIZ — retry uchun kerak
    await state.set_state(None)


# ─────────────────────────── Xatolarni qayta ishlash ───────────────────────────


@router.callback_query(F.data.startswith("qp:retry:"))
async def retry_wrong_answers(cb: CallbackQuery, state: FSMContext) -> None:
    parts = cb.data.split(":")
    quiz_id = parts[2]
    set_number = int(parts[3])

    data = await state.get_data()
    wrong_ids = data.get("wrong_question_ids", [])
    all_questions = data.get("questions", [])
    time_sec = data.get("time_sec", 30)

    if not wrong_ids or not all_questions:
        try:
            all_questions = await ai_engine_client().get_questions(quiz_id, set_number)
            wrong_ids = list(range(len(all_questions)))
        except Exception:
            await cb.answer("Savollarni yuklab bo'lmadi", show_alert=True)
            return

    wrong_questions = [all_questions[i] for i in wrong_ids if i < len(all_questions)]

    if not wrong_questions:
        await cb.answer("Hech qanday xato savol topilmadi", show_alert=True)
        return

    await state.set_state(QuizStates.QUIZ_PLAYING)
    await state.update_data(
        questions=wrong_questions,
        total=len(wrong_questions),
        current_q_index=0,
        correct=0,
        wrong=0,
        skipped=0,
        skip_count=0,
        wrong_question_ids=[],
        current_poll_id=None,
        quiz_id=quiz_id,
        set_number=set_number,
        time_sec=time_sec,
        is_retry=True,
    )

    await cb.message.answer(
        f"🔁 {len(wrong_questions)} ta xato savolni qayta ishlash boshlanadi..."
    )
    await cb.answer()
    await _send_next_question(cb.message.chat.id, cb.from_user.id, state, cb.bot)


@router.callback_query(F.data.startswith("qp:show_wrong:"))
async def show_wrong_answers(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    wrong_ids = data.get("wrong_question_ids", [])
    questions = data.get("questions", [])

    if not wrong_ids:
        await cb.answer("Xato savollar yo'q!", show_alert=True)
        return

    text = "📊 Xato javob berilgan savollar:\n\n"
    for i, idx in enumerate(wrong_ids[:10], 1):
        if idx < len(questions):
            q = questions[idx]
            q_text = q.get("question_text", q.get("question", "?"))[:80]
            text += f"{i}. {q_text}...\n"

    if len(wrong_ids) > 10:
        text += f"\n...va yana {len(wrong_ids) - 10} ta savol"

    quiz_id = data.get("quiz_id", "")
    set_number = data.get("set_number", 1)

    await cb.message.answer(
        text,
        reply_markup=retry_result_keyboard(quiz_id, set_number, len(wrong_ids)),
    )
    await cb.answer()


# ─────────────────────────── Qidiruv ───────────────────────────


@router.message(F.text.in_({"🔍 Qidirish", "🔍 Search", "🔍 Поиск"}))
async def search_menu(message: Message, state: FSMContext) -> None:
    await state.set_state(QuizStates.SEARCHING)
    data = await state.get_data()
    lang = data.get("language_code", "uz")
    try:
        tags_data = await ai_engine_client().get_trending_tags(limit=9)
        if isinstance(tags_data, list) and tags_data and isinstance(tags_data[0], dict):
            tag_names = [f"#{t['slug']}" for t in tags_data]
        elif isinstance(tags_data, list):
            tag_names = [f"#{t}" for t in tags_data]
        else:
            tag_names = ["#dtm", "#ingliz_tili", "#matematika"]
    except Exception:
        tag_names = ["#dtm", "#ingliz_tili", "#matematika"]

    tags_text = "  ".join(tag_names)
    await message.answer(t("quiz_search_prompt", lang) + f"\n\n{tags_text}")


_MENU_BUTTONS = {
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


@router.message(QuizStates.SEARCHING, ~F.text.in_(_MENU_BUTTONS))
async def handle_search(message: Message, state: FSMContext) -> None:
    query = message.text.strip()
    tag = None
    if query.startswith("#"):
        tag = query.lstrip("#").lower()
        query = None

    fsm_data = await state.get_data()
    lang = fsm_data.get("language_code", "uz")

    try:
        data = await ai_engine_client().get_quizzes(search=query, tag=tag)
        quizzes = data.get("quizzes", []) if isinstance(data, dict) else (data or [])
    except Exception:
        quizzes = []

    if not quizzes:
        await message.answer(t("quiz_not_found", lang))
        return

    await message.answer(
        f"Natijalar: <b>{message.text}</b>",
        reply_markup=quiz_list_keyboard(quizzes),
    )
    await state.clear()
