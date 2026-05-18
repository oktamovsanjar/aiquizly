"""
Telegram Guruhda Ishlash — BOT_UX.md §14.

Telegram guruh = haqiqiy Telegram chat (guruh yoki supergroup).
Quiz guruh (§13) ≠ bu yerda muhokama qilinayotgan narsa.

Handler oqimlari:
  §14.1 — Bot guruhga qo'shilganda xush kelibsiz xabari
  §14.2 — /settings (admin) — voting, who_can_start sozlamalari
  §14.3 — /quiz (guruh ichida) — voting yoki to'g'ridan-to'g'ri boshlash
  §14.4 — Quiz jarayoni: har savol Poll, natijalar leaderboard
  §14.5 — /top — guruh reytingi
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from aiogram import Bot, F, Router
from aiogram.filters import Command, IS_MEMBER, IS_NOT_MEMBER, ChatMemberUpdatedFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    Message,
    PollAnswer,
)
from sqlalchemy import select, update

from db import AsyncSessionLocal
from db.models import TelegramGroup, User
from fsm.states import QuizStates
from keyboards.inline import (
    tg_group_settings_keyboard,
    voting_keyboard,
    group_result_keyboard,
)

logger = logging.getLogger(__name__)
router = Router()
# Faqat guruh/superguruhda ishlaydi
router.message.filter(F.chat.type.in_({"group", "supergroup"}))
router.callback_query.filter(F.message.chat.type.in_({"group", "supergroup"}))

# ── Voting state key helpers ──────────────────────────────────────────────────

_VOTING_KEY = "tg_voting_{chat_id}"
_QUIZ_KEY   = "tg_quiz_{chat_id}"

# In-memory store for active group sessions (chat_id → session dict)
# This is sufficient for single-instance deployments; for HA use Redis.
_group_sessions: dict[int, dict] = {}


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_or_create_group(chat_id: int, title: str | None) -> TelegramGroup:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(TelegramGroup).where(TelegramGroup.chat_id == chat_id)
        )
        group = result.scalar_one_or_none()
        if not group:
            group = TelegramGroup(chat_id=chat_id, title=title)
            session.add(group)
            await session.commit()
            await session.refresh(group)
        return group


async def _is_chat_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


# ── §14.1  Bot guruhga qo'shildi ─────────────────────────────────────────────


@router.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def bot_added_to_group(event: ChatMemberUpdated) -> None:
    """Bot yangi guruhga qo'shilganda xush kelibsiz xabar."""
    if event.chat.type not in ("group", "supergroup"):
        return

    await _get_or_create_group(event.chat.id, event.chat.title)

    await event.answer(
        "👋 <b>Quiz Bot guruhga qo'shildi!</b>\n\n"
        "Admin buyruqlari:\n"
        "/quiz — quiz boshlash\n"
        "/settings — guruh sozlamalari\n"
        "/top — guruh reytingi\n\n"
        "Quizni boshlash uchun /quiz buyrug'ini yuboring!"
    )


# ── §14.2  /settings — admin sozlamalari ─────────────────────────────────────


@router.message(Command("settings"), F.chat.type.in_({"group", "supergroup"}))
async def group_settings(message: Message, state: FSMContext) -> None:
    """Admin guruh sozlamalarini ko'radi/o'zgartiradi."""
    if not await _is_chat_admin(message.bot, message.chat.id, message.from_user.id):
        await message.reply("⛔ Bu buyruq faqat adminlar uchun.")
        return

    group = await _get_or_create_group(message.chat.id, message.chat.title)

    await message.reply(
        "⚙️ <b>Guruh sozlamalari:</b>",
        reply_markup=tg_group_settings_keyboard(
            voting=group.voting_enabled,
            who=group.who_can_start,
        ),
    )
    await state.set_state(QuizStates.TG_GROUP_SETTINGS)
    await state.update_data(settings_chat_id=message.chat.id)


@router.callback_query(QuizStates.TG_GROUP_SETTINGS, F.data == "tg:toggle_voting")
async def toggle_voting(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    chat_id = data.get("settings_chat_id")
    if not chat_id:
        await cb.answer()
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(TelegramGroup).where(TelegramGroup.chat_id == chat_id)
        )
        group = result.scalar_one_or_none()
        if group:
            group.voting_enabled = not group.voting_enabled
            await session.commit()
            await cb.message.edit_reply_markup(
                reply_markup=tg_group_settings_keyboard(
                    voting=group.voting_enabled,
                    who=group.who_can_start,
                )
            )
    await cb.answer()


@router.callback_query(QuizStates.TG_GROUP_SETTINGS, F.data.startswith("tg:who:"))
async def set_who_can_start(cb: CallbackQuery, state: FSMContext) -> None:
    who = cb.data.split(":")[2]  # "admin" | "all"
    data = await state.get_data()
    chat_id = data.get("settings_chat_id")
    if not chat_id:
        await cb.answer()
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(TelegramGroup).where(TelegramGroup.chat_id == chat_id)
        )
        group = result.scalar_one_or_none()
        if group:
            group.who_can_start = who
            await session.commit()
            await cb.message.edit_reply_markup(
                reply_markup=tg_group_settings_keyboard(
                    voting=group.voting_enabled,
                    who=group.who_can_start,
                )
            )
    await cb.answer("✅ Saqlandi")


@router.callback_query(QuizStates.TG_GROUP_SETTINGS, F.data == "tg:save_settings")
async def save_settings(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.edit_text("✅ Sozlamalar saqlandi.")
    await cb.answer()


# ── §14.3  /quiz — guruhda quiz boshlash ─────────────────────────────────────


@router.message(Command("quiz"), F.chat.type.in_({"group", "supergroup"}))
async def group_quiz_command(message: Message, state: FSMContext, bot: Bot) -> None:
    """
    Guruhda /quiz buyruqi.
    Voting yoqilgan → voting o'tkaziladi.
    Voting o'chirilgan → admin darhol tanlaydi.
    """
    group = await _get_or_create_group(message.chat.id, message.chat.title)
    chat_id = message.chat.id
    user_id = message.from_user.id

    is_admin = await _is_chat_admin(bot, chat_id, user_id)

    # Kim boshlashi mumkin?
    if group.who_can_start == "admin" and not is_admin:
        await message.reply("⛔ Quizni faqat admin boshlay oladi.")
        return

    # Demo: fixed quiz info (real implementatsiyada DB dan o'qiladi)
    quiz_name = "Umumiy bilimlar"
    set_number = 1
    question_count = 10
    time_per_q = 30

    if group.voting_enabled:
        # Voting boshlanadi
        vote_msg = await message.reply(
            f"🗳 <b>Quiz boshlashga ovoz bering!</b>\n\n"
            f"📋 <b>{quiz_name}</b> — Set {set_number} ({question_count} savol)\n"
            f"⏱ Har savol: {time_per_q} soniya\n\n"
            f"Boshlash uchun kamida {group.min_voters} kishi kerak.\n\n"
            f"✅ Tayyorman: 0 kishi\n"
            f"⏳ Kutish: {group.voting_timeout} soniya",
            reply_markup=voting_keyboard(msg_id=message.message_id, voter_count=0),
        )

        # Session saqlash
        _group_sessions[chat_id] = {
            "phase": "voting",
            "vote_msg_id": vote_msg.message_id,
            "voters": set(),
            "quiz_name": quiz_name,
            "set_number": set_number,
            "question_count": question_count,
            "time_per_q": time_per_q,
            "min_voters": group.min_voters,
            "started_by": user_id,
            "scores": {},
        }

        # Timeout boshlanadi
        asyncio.create_task(
            _voting_timeout(bot, chat_id, vote_msg.message_id, group.voting_timeout)
        )
    else:
        # Voting o'chirilgan — darhol boshlash
        if not is_admin:
            await message.reply("⛔ Quizni faqat admin boshlaya oladi.")
            return
        _group_sessions[chat_id] = {
            "phase": "playing",
            "quiz_name": quiz_name,
            "set_number": set_number,
            "question_count": question_count,
            "time_per_q": time_per_q,
            "current_q": 0,
            "scores": {},
            "participants": set(),
        }
        await _start_group_quiz(bot, chat_id)


# ── Voting timeout ────────────────────────────────────────────────────────────


async def _voting_timeout(bot: Bot, chat_id: int, vote_msg_id: int, timeout: int) -> None:
    await asyncio.sleep(timeout)
    session = _group_sessions.get(chat_id)
    if not session or session.get("phase") != "voting":
        return

    voter_count = len(session.get("voters", set()))
    min_voters = session.get("min_voters", 3)

    if voter_count < min_voters:
        _group_sessions.pop(chat_id, None)
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=vote_msg_id,
                text=(
                    f"❌ Yetarli ishtirokchi yo'q.\n"
                    f"({voter_count}/{min_voters} kishi ovoz berdi)"
                ),
            )
        except Exception:
            pass
        return

    # Yetarli ovoz — quiz boshlanadi
    session["phase"] = "playing"
    session["current_q"] = 0
    session["participants"] = set(session["voters"])
    await _start_group_quiz(bot, chat_id)


# ── Voting callback ───────────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("tg:vote:"))
async def handle_vote(cb: CallbackQuery) -> None:
    chat_id = cb.message.chat.id
    session = _group_sessions.get(chat_id)
    if not session or session.get("phase") != "voting":
        await cb.answer("Voting tugagan yoki mavjud emas.", show_alert=True)
        return

    voters: set = session.setdefault("voters", set())
    user_id = cb.from_user.id

    if user_id in voters:
        await cb.answer("Siz allaqachon ovoz berdingiz!", show_alert=True)
        return

    voters.add(user_id)
    voter_count = len(voters)

    # Tugmacha yangilash
    try:
        await cb.message.edit_reply_markup(
            reply_markup=voting_keyboard(
                msg_id=cb.message.message_id,
                voter_count=voter_count,
            )
        )
        # Xabar matnini ham yangilaymiz
        quiz_name = session.get("quiz_name", "Quiz")
        set_number = session.get("set_number", 1)
        q_count = session.get("question_count", 10)
        time_per_q = session.get("time_per_q", 30)
        min_voters = session.get("min_voters", 3)
        await cb.message.edit_text(
            f"🗳 <b>Quiz boshlashga ovoz bering!</b>\n\n"
            f"📋 <b>{quiz_name}</b> — Set {set_number} ({q_count} savol)\n"
            f"⏱ Har savol: {time_per_q} soniya\n\n"
            f"Boshlash uchun kamida {min_voters} kishi kerak.\n\n"
            f"✅ Tayyorman: {voter_count} kishi",
            reply_markup=voting_keyboard(
                msg_id=cb.message.message_id,
                voter_count=voter_count,
            ),
        )
    except Exception:
        pass

    await cb.answer(f"✅ Ovoz qabul qilindi! ({voter_count} kishi)")


@router.callback_query(F.data.startswith("tg:force_start:"))
async def force_start_voting(cb: CallbackQuery, bot: Bot) -> None:
    """Admin voting ni kutmasdan darhol boshlaydi."""
    chat_id = cb.message.chat.id
    if not await _is_chat_admin(bot, chat_id, cb.from_user.id):
        await cb.answer("⛔ Faqat admin!", show_alert=True)
        return

    session = _group_sessions.get(chat_id)
    if not session or session.get("phase") != "voting":
        await cb.answer("Voting topilmadi.", show_alert=True)
        return

    session["phase"] = "playing"
    session["current_q"] = 0
    session["participants"] = set(session.get("voters", set()))

    try:
        await cb.message.edit_text("🚀 Admin quiz boshladi!")
    except Exception:
        pass

    await _start_group_quiz(bot, chat_id)
    await cb.answer()


# ── §14.4  Quiz jarayoni ──────────────────────────────────────────────────────


# Demo savollar (real implementatsiyada Game service / DB dan keladi)
_DEMO_QUESTIONS = [
    {
        "question": "O'zbekistonning poytaxti qaysi shahar?",
        "options": ["Samarqand", "Toshkent", "Buxoro", "Namangan"],
        "correct": 1,
    },
    {
        "question": "Quyosh sistemasidagi eng katta sayyora?",
        "options": ["Saturn", "Neptun", "Yupiter", "Uran"],
        "correct": 2,
    },
    {
        "question": "Suvning kimyoviy formulasi?",
        "options": ["CO2", "H2O2", "H2O", "NaCl"],
        "correct": 2,
    },
    {
        "question": "1 + 1 = ?",
        "options": ["1", "2", "3", "11"],
        "correct": 1,
    },
    {
        "question": "Eng katta okean?",
        "options": ["Atlantika", "Hind", "Arktika", "Tinch"],
        "correct": 3,
    },
]


async def _start_group_quiz(bot: Bot, chat_id: int) -> None:
    session = _group_sessions.get(chat_id)
    if not session:
        return

    q_count = min(session.get("question_count", 5), len(_DEMO_QUESTIONS))
    session["question_count"] = q_count
    session["poll_ids"] = {}  # poll_id → question_index

    await bot.send_message(
        chat_id,
        f"🎯 <b>{session.get('quiz_name', 'Quiz')} boshlanmoqda!</b>\n"
        f"Jami {q_count} ta savol. Har biri {session.get('time_per_q', 30)} soniya.",
    )
    await asyncio.sleep(2)
    await _send_next_question(bot, chat_id)


async def _send_next_question(bot: Bot, chat_id: int) -> None:
    session = _group_sessions.get(chat_id)
    if not session:
        return

    idx = session.get("current_q", 0)
    q_count = session.get("question_count", 5)

    if idx >= q_count:
        await _show_group_results(bot, chat_id)
        return

    q = _DEMO_QUESTIONS[idx % len(_DEMO_QUESTIONS)]
    time_limit = session.get("time_per_q", 30)

    sent = await bot.send_poll(
        chat_id=chat_id,
        question=f"❓ {idx + 1}/{q_count}: {q['question']}",
        options=q["options"],
        type="quiz",
        correct_option_id=q["correct"],
        is_anonymous=False,
        open_period=time_limit,
    )

    session["poll_ids"][sent.poll.id] = idx
    session["current_q"] = idx + 1

    # Keyingi savolga o'tish — poll muddati + 1 soniya
    asyncio.create_task(
        _wait_and_next(bot, chat_id, time_limit + 1)
    )


async def _wait_and_next(bot: Bot, chat_id: int, delay: int) -> None:
    await asyncio.sleep(delay)
    session = _group_sessions.get(chat_id)
    if session and session.get("phase") == "playing":
        await _send_next_question(bot, chat_id)


# ── Poll answer tracking ──────────────────────────────────────────────────────


@router.poll_answer()
async def on_group_poll_answer(poll_answer: PollAnswer, bot: Bot) -> None:
    """
    Guruh polllarini kuzatish.
    Faqat _group_sessions ichidagi poll_id lar uchun ishlaydi.
    """
    poll_id = poll_answer.poll_id
    user_id = poll_answer.user.id
    selected = poll_answer.option_ids  # bo'sh = skip/timeout

    # Qaysi guruhga tegishli ekanini topamiz
    target_chat: int | None = None
    for chat_id, session in _group_sessions.items():
        if poll_id in session.get("poll_ids", {}):
            target_chat = chat_id
            break

    if target_chat is None:
        return

    session = _group_sessions[target_chat]
    if not selected:
        return  # Timeout yoki skip — ball berilmaydi

    q_idx = session["poll_ids"][poll_id]
    q = _DEMO_QUESTIONS[q_idx % len(_DEMO_QUESTIONS)]
    correct_idx = q["correct"]

    scores: dict = session.setdefault("scores", {})
    if user_id not in scores:
        scores[user_id] = {"correct": 0, "wrong": 0, "name": poll_answer.user.full_name}

    if selected[0] == correct_idx:
        scores[user_id]["correct"] += 1
    else:
        scores[user_id]["wrong"] += 1


# ── Natijalar ─────────────────────────────────────────────────────────────────


async def _show_group_results(bot: Bot, chat_id: int) -> None:
    session = _group_sessions.pop(chat_id, None)
    if not session:
        return

    scores: dict = session.get("scores", {})
    q_count = session.get("question_count", 5)

    if not scores:
        await bot.send_message(chat_id, "🏁 Quiz tugadi. Hech kim javob bermadi.")
        return

    # Saralash: to'g'ri javoblar bo'yicha kamayib
    ranked = sorted(scores.items(), key=lambda x: x[1]["correct"], reverse=True)

    medals = ["🥇", "🥈", "🥉"]
    lines = []
    total_correct = 0

    for i, (uid, info) in enumerate(ranked):
        medal = medals[i] if i < 3 else f"{i + 1}."
        lines.append(
            f"{medal} {info['name']} — {info['correct']}/{q_count}"
        )
        total_correct += info["correct"]

    avg_pct = int(total_correct / (len(ranked) * q_count) * 100) if ranked else 0
    participant_count = len(ranked)

    text = (
        f"🏁 <b>Quiz natijasi:</b>\n\n"
        + "\n".join(lines)
        + f"\n\n👥 Qatnashganlar: {participant_count} kishi\n"
        f"📊 O'rtacha: {avg_pct}%"
    )

    await bot.send_message(chat_id, text, reply_markup=group_result_keyboard())


# ── §14.5  /top — guruh reytingi ─────────────────────────────────────────────


@router.message(Command("top"), F.chat.type.in_({"group", "supergroup"}))
async def group_top(message: Message) -> None:
    """Guruh ichida eng yaxshi o'yinchilar reytingi."""
    # Real implementatsiyada Game service / DB dan o'qiladi
    await message.reply(
        "📊 <b>Guruh reytingi:</b>\n\n"
        "🥇 Hali o'yinlar yo'q.\n\n"
        "Quiz o'ynash uchun /quiz bosing!",
    )


# ── Replay ────────────────────────────────────────────────────────────────────


@router.callback_query(F.data == "tg:replay")
async def group_replay(cb: CallbackQuery, bot: Bot) -> None:
    """Guruhda yana o'ynash — oxirgi quiz sozlamalarini qayta ishga tushiradi."""
    chat_id = cb.message.chat.id
    if not await _is_chat_admin(bot, chat_id, cb.from_user.id):
        await cb.answer("⛔ Faqat admin qayta boshlaya oladi!", show_alert=True)
        return

    if chat_id in _group_sessions:
        await cb.answer("Quiz hozir ham davom etmoqda!", show_alert=True)
        return

    _group_sessions[chat_id] = {
        "phase": "playing",
        "quiz_name": "Umumiy bilimlar",
        "set_number": 1,
        "question_count": 5,
        "time_per_q": 30,
        "current_q": 0,
        "scores": {},
        "participants": set(),
    }

    await cb.message.edit_reply_markup(reply_markup=None)
    await _start_group_quiz(bot, chat_id)
    await cb.answer()
