"""Quiz oqimi — ko'rish, tanlash, o'ynash, to'xtatish, natijalar."""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery, Message, PollAnswer,
    InlineKeyboardButton, InlineKeyboardMarkup,
)

from fsm.states import QuizStates
from keyboards.inline import (
    quiz_browse_keyboard, quiz_list_keyboard, set_select_keyboard,
    time_select_keyboard, quiz_start_keyboard, stop_quiz_keyboard,
    pause_quiz_keyboard, quiz_result_keyboard, retry_result_keyboard,
    subscribe_group_keyboard,
)
from utils.api import ai_engine_client, game_client

logger = logging.getLogger(__name__)

# Auto-pause: 2 ta ketma-ket skip bo'lsa pauza
AUTO_PAUSE_SKIP_COUNT = 2

router = Router()


# ─────────────────────────── Boshlash menyusi ───────────────────────────

@router.message(F.text.in_({"▶️ Boshlash", "▶️ Start", "▶️ Начать"}))
@router.message(Command("quiz"))
async def quiz_start_menu(message: Message, state: FSMContext) -> None:
    await state.set_state(QuizStates.BROWSING_MY_QUIZZES)
    await message.answer(
        "Qayerdan o'ynaysiz?",
        reply_markup=quiz_browse_keyboard(),
    )


@router.callback_query(F.data == "qb:menu")
async def back_to_menu(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.edit_text(
        "Qayerdan o'ynaysiz?",
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
        quizzes = data.get("quizzes", data) if isinstance(data, dict) else data
    except Exception:
        quizzes = []

    if not quizzes:
        await cb.message.edit_text(
            "📂 Sizda hali quizlar yo'q.\n\n"
            "Fayl yuklash orqali yarating!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📤 Quiz yaratish", callback_data="up:menu")],
                [InlineKeyboardButton(text="🏠 Menyu", callback_data="qb:menu")],
            ]),
        )
        await cb.answer()
        return

    await cb.message.edit_text(
        "📂 Sizning to'plamlaringiz:",
        reply_markup=quiz_list_keyboard(quizzes),
    )
    await cb.answer()


# ─────────────────────────── Obunalarim ───────────────────────────

@router.callback_query(F.data == "qb:subs")
async def browse_subscriptions(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(QuizStates.BROWSING_SUBSCRIPTIONS)
    # DB dan foydalanuvchining obunalarini olish
    from db import AsyncSessionLocal
    from db.models import QuizGroupSubscriber, QuizGroup, User
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(QuizGroup)
            .join(QuizGroupSubscriber, QuizGroupSubscriber.quiz_group_id == QuizGroup.id)
            .join(User, User.id == QuizGroupSubscriber.user_id)
            .where(User.telegram_id == cb.from_user.id)
            .where(QuizGroup.is_active == True)
        )
        groups = result.scalars().all()

    if not groups:
        await cb.message.edit_text(
            "📌 Siz hali hech qaysi quiz guruhiga obuna bo'lmagansiz.\n\n"
            "Ommaviy quizlarda guruhlarni topishingiz mumkin.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🌐 Ommaviy quizlar", callback_data="qb:public")],
                [InlineKeyboardButton(text="🏠 Menyu", callback_data="qb:menu")],
            ]),
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
            quizzes_all = data.get("quizzes", data) if isinstance(data, dict) else data
            if quizzes_all:
                random.shuffle(quizzes_all)
                data = {"quizzes": quizzes_all[:5]}
        else:
            data = await ai_engine_client().get_quizzes(public=True)
        quizzes = data.get("quizzes", data) if isinstance(data, dict) else data
    except Exception:
        quizzes = []

    if not quizzes:
        await cb.message.edit_text(
            "🌐 Hozircha ommaviy quizlar yo'q.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Menyu", callback_data="qb:menu")]
            ]),
        )
        await cb.answer()
        return

    await cb.message.edit_text(
        "🌐 Ommaviy quizlar:",
        reply_markup=quiz_list_keyboard(quizzes),
    )
    await cb.answer()


# ─────────────────────────── Quiz tanlash → Set tanlash ───────────────────────────

@router.callback_query(F.data.startswith("qb:quiz:"))
async def select_quiz(cb: CallbackQuery, state: FSMContext) -> None:
    quiz_id = cb.data.split(":")[2]
    try:
        quiz = await ai_engine_client().get_quiz(quiz_id)
    except Exception:
        await cb.answer("Quiz topilmadi", show_alert=True)
        return

    # Setlarni ko'rsatish (20 tadan bo'lingan)
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


# ─────────────────────────── Set → Vaqt tanlash ───────────────────────────

@router.callback_query(F.data.startswith("qp:set:"))
async def select_set(cb: CallbackQuery, state: FSMContext) -> None:
    parts = cb.data.split(":")
    quiz_id = parts[2]
    set_number = int(parts[3])

    await state.update_data(quiz_id=quiz_id, set_number=set_number, time_sec=30)
    await state.set_state(QuizStates.QUIZ_SETUP)

    await cb.message.edit_text(
        f"⏱ Har bir savol uchun vaqt:\n\n💡 Tavsiya: 30 soniya",
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

    await state.update_data(time_sec=time_sec)

    await cb.message.edit_text(
        f"📋 <b>{quiz_title}</b> — Set {set_number}\n"
        f"⏱ Har savol: {time_sec} soniya\n\n"
        "Tayyormisiz?",
        reply_markup=quiz_start_keyboard(quiz_id, set_number, time_sec),
    )
    await cb.answer()


# ─────────────────────────── Quiz boshlash ───────────────────────────

@router.callback_query(F.data.startswith("qp:start:"))
async def start_quiz(cb: CallbackQuery, state: FSMContext) -> None:
    parts = cb.data.split(":")
    quiz_id = parts[2]
    set_number = int(parts[3])
    time_sec = int(parts[4])

    await state.set_state(QuizStates.QUIZ_PLAYING)
    await state.update_data(
        quiz_id=quiz_id, set_number=set_number, time_sec=time_sec,
        current_q_index=0, skip_count=0,
        correct=0, wrong=0, skipped=0,
    )

    # Savollarni olish
    try:
        questions = await ai_engine_client().get_questions(quiz_id, set_number)
    except Exception:
        await cb.message.edit_text("❌ Savollarni yuklab bo'lmadi. Qaytadan urinib ko'ring.")
        await state.clear()
        await cb.answer()
        return

    if not questions:
        await cb.message.edit_text("❌ Bu setda savollar topilmadi.")
        await state.clear()
        await cb.answer()
        return

    await state.update_data(questions=questions, total=len(questions))

    # Game service da game yaratish
    try:
        game_data = await game_client().start_game(
            user_id=cb.from_user.id,
            quiz_id=quiz_id,
            set_number=set_number,
            time_per_question=time_sec,
        )
        await state.update_data(game_id=game_data.get("game_id"))
    except Exception:
        pass  # game service bo'lmasa ham quiz ketadi

    await cb.message.delete()
    await cb.answer()

    # Birinchi savolni yuborish
    await _send_next_question(cb.message.chat.id, state, cb.bot)


async def _send_next_question(chat_id: int, state: FSMContext, bot) -> None:
    data = await state.get_data()
    questions = data.get("questions", [])
    idx = data.get("current_q_index", 0)
    total = data.get("total", len(questions))
    time_sec = data.get("time_sec", 30)

    if idx >= total:
        # Barcha savollar tugadi
        await _show_results(chat_id, state, bot)
        return

    q = questions[idx]
    options = q.get("options", [])
    correct_idx = q.get("correct_indices", [0])[0] if q.get("correct_indices") else q.get("correct_index", 0)

    msg = await bot.send_poll(
        chat_id=chat_id,
        question=f"({idx + 1}/{total}) {q.get('question_text', q.get('question', ''))}",
        options=options,
        type="quiz",
        correct_option_id=correct_idx,
        explanation=q.get("explanation") or None,
        open_period=time_sec,
        is_anonymous=False,
    )

    await state.update_data(
        current_poll_id=msg.poll.id,
        current_poll_msg_id=msg.message_id,
        current_q_index=idx + 1,
    )


@router.poll_answer()
async def on_poll_answer(poll_answer: PollAnswer, state: FSMContext) -> None:
    """Foydalanuvchi poll ga javob berganda"""
    data = await state.get_data()
    if not data.get("questions"):
        return

    idx = data.get("current_q_index", 1) - 1
    questions = data.get("questions", [])
    if idx < 0 or idx >= len(questions):
        return

    q = questions[idx]
    correct_indices = q.get("correct_indices", [q.get("correct_index", 0)])
    selected = poll_answer.option_ids

    # Vaqt tugasa Telegram [] yuboradi — skip hisoblanadi
    is_skipped = len(selected) == 0
    is_correct = not is_skipped and sorted(selected) == sorted(correct_indices)

    if is_correct:
        await state.update_data(
            correct=data.get("correct", 0) + 1,
            skip_count=0,
        )
    elif is_skipped:
        skip_count = data.get("skip_count", 0) + 1
        await state.update_data(
            skipped=data.get("skipped", 0) + 1,
            skip_count=skip_count,
        )
        # Auto-pause: 2 ta ketma-ket skip
        if skip_count >= AUTO_PAUSE_SKIP_COUNT:
            await state.set_state(QuizStates.PAUSED)
            await state.update_data(skip_count=0)
            await poll_answer.bot.send_message(
                poll_answer.user.id,
                "⏸ Avtomatik pauza!\n"
                f"{skip_count} ta ketma-ket javob berilmadi.\n\n"
                "Quizni davom ettirishga tayyormisiz?",
                reply_markup=pause_quiz_keyboard(),
            )
            return
    else:
        # Noto'g'ri javob — wrong savolni eslab qo'yamiz
        wrong_q_ids = data.get("wrong_question_ids", [])
        wrong_q_ids.append(idx)
        await state.update_data(
            wrong=data.get("wrong", 0) + 1,
            skip_count=0,
            wrong_question_ids=wrong_q_ids,
        )

    # Keyingi savolga o'tish
    await _send_next_question(poll_answer.user.id, state, poll_answer.bot)


# ─────────────────────────── To'xtatish / Pauza ───────────────────────────

@router.message(Command("stop"))
@router.callback_query(F.data == "qp:stop")
async def stop_quiz(event, state: FSMContext) -> None:
    """Quizni to'xtatish"""
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
    await _show_results(cb.message.chat.id, state, cb.bot, message=cb.message)
    await cb.answer()


@router.callback_query(F.data == "qp:stop_save")
async def stop_and_save(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    game_id = data.get("game_id")
    if game_id:
        try:
            await game_client().finish_game(game_id, status="saved")
        except Exception:
            pass
    await state.clear()
    await cb.message.edit_text("💾 Progress saqlandi. Keyinroq davom etishingiz mumkin.")
    await cb.answer()


@router.callback_query(F.data == "qp:continue")
async def continue_quiz(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(QuizStates.QUIZ_PLAYING)
    await cb.message.delete()
    await cb.answer()
    await _send_next_question(cb.message.chat.id, state, cb.bot)


# ─────────────────────────── Natijalar ───────────────────────────

async def _show_results(chat_id: int, state: FSMContext, bot, message=None) -> None:
    data = await state.get_data()
    correct = data.get("correct", 0)
    wrong = data.get("wrong", 0)
    skipped = data.get("skipped", 0)
    total = data.get("total", correct + wrong + skipped)
    quiz_id = data.get("quiz_id", "")
    set_number = data.get("set_number", 1)
    time_sec = data.get("time_sec", 30)
    game_id = data.get("game_id")

    score = int((correct / total * 1000)) if total > 0 else 0

    # 100% natija emoji
    perfect = correct == total and total > 0
    header = "💯 Mukammal!" if perfect else "🏁 Quiz tugadi!"

    # Game servisni tugatish
    xp_earned = 0
    new_achievements = []
    if game_id:
        try:
            result = await game_client().finish_game(game_id, status="completed")
            xp_earned = result.get("xp_earned", 0)
            new_achievements = result.get("new_achievements", [])
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

    # Keyingi set bormi?
    next_set = set_number + 1 if (correct + wrong + skipped) >= total and total > 0 else None

    kb = quiz_result_keyboard(
        quiz_id=quiz_id,
        set_number=set_number,
        next_set=next_set,
        has_wrong=wrong > 0,
        time_sec=time_sec,
    )

    if message:
        await message.answer(text, reply_markup=kb)
    else:
        await bot.send_message(chat_id, text, reply_markup=kb)

    await state.clear()


# ─────────────────────────── Xatolarni qayta ishlash ───────────────────────────

@router.callback_query(F.data.startswith("qp:retry:"))
async def retry_wrong_answers(cb: CallbackQuery, state: FSMContext) -> None:
    """Noto'g'ri javob berilgan savollarni qayta o'ynash."""
    parts = cb.data.split(":")
    quiz_id = parts[2]
    set_number = int(parts[3])

    # Oldingi sessiyada xato savollar indekslarini olish
    data = await state.get_data()
    wrong_ids = data.get("wrong_question_ids", [])
    all_questions = data.get("questions", [])

    if not wrong_ids or not all_questions:
        # Qaytadan savollarni yuklab olamiz
        try:
            all_questions = await ai_engine_client().get_questions(quiz_id, set_number)
            wrong_ids = list(range(len(all_questions)))  # hammasini retry qilamiz
        except Exception:
            await cb.answer("Savollarni yuklab bo'lmadi", show_alert=True)
            return

    wrong_questions = [all_questions[i] for i in wrong_ids if i < len(all_questions)]

    if not wrong_questions:
        await cb.answer("Hech qanday xato savol topilmadi", show_alert=True)
        return

    time_sec = data.get("time_sec", 30)

    await state.set_state(QuizStates.QUIZ_PLAYING)
    await state.update_data(
        questions=wrong_questions,
        total=len(wrong_questions),
        current_q_index=0,
        correct=0, wrong=0, skipped=0,
        skip_count=0,
        wrong_question_ids=[],
        quiz_id=quiz_id, set_number=set_number, time_sec=time_sec,
        is_retry=True,
    )

    await cb.message.answer(
        f"🔁 {len(wrong_questions)} ta xato savolni qayta ishlash boshlanadi..."
    )
    await cb.answer()
    await _send_next_question(cb.message.chat.id, state, cb.bot)


@router.callback_query(F.data.startswith("qp:show_wrong:"))
async def show_wrong_answers(cb: CallbackQuery, state: FSMContext) -> None:
    """Xato savollarni ro'yxat sifatida ko'rsatish."""
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
    await message.answer(
        f"🔍 Qidiring yoki teg tanlang:\n\n"
        f"Trenddagi teglar:\n{tags_text}\n\n"
        "Yoki matn yozing..."
    )


@router.message(QuizStates.SEARCHING)
async def handle_search(message: Message, state: FSMContext) -> None:
    query = message.text.strip()
    tag = None
    if query.startswith("#"):
        tag = query.lstrip("#").lower()
        query = None

    try:
        data = await ai_engine_client().get_quizzes(search=query, tag=tag)
        quizzes = data.get("quizzes", data) if isinstance(data, dict) else data
    except Exception:
        quizzes = []

    if not quizzes:
        await message.answer(
            f"🔍 '{message.text}' bo'yicha natija topilmadi.\n"
            "Boshqa so'z bilan qidiring.",
        )
        return

    await message.answer(
        f"Natijalar: <b>{message.text}</b>",
        reply_markup=quiz_list_keyboard(quizzes),
    )
    await state.clear()
