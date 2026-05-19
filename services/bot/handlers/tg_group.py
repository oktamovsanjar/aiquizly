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
import json
import logging

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
from db.models import TelegramGroup
from fsm.states import QuizStates
from keyboards.inline import (
    tg_group_settings_keyboard,
    tg_group_linked_quizzes_keyboard,
    tg_group_quiz_select_keyboard,
    tg_group_quiz_start_keyboard,
    voting_keyboard,
    group_result_keyboard,
)
from utils.api import ai_engine_client

logger = logging.getLogger(__name__)
router = Router()
# Faqat guruh/superguruhda ishlaydi
router.message.filter(F.chat.type.in_({"group", "supergroup"}))
router.callback_query.filter(F.message.chat.type.in_({"group", "supergroup"}))

# ── Voting state key helpers ──────────────────────────────────────────────────

_VOTING_KEY = "tg_voting_{chat_id}"
_QUIZ_KEY = "tg_quiz_{chat_id}"

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
        "/stop — quizni to'xtatish\n"
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

    if message.chat.id in _group_sessions:
        await message.reply(
            "⚠️ Hozir quiz jarayoni davom etmoqda.\n"
            "Sozlamalarni o'zgartirish uchun avval /stop bilan to'xtating."
        )
        return

    group = await _get_or_create_group(message.chat.id, message.chat.title)

    linked_ids = json.loads(group.linked_quiz_ids or "[]")
    linked_count = len(linked_ids)

    await message.reply(
        "⚙️ <b>Guruh sozlamalari:</b>",
        reply_markup=tg_group_settings_keyboard(
            who=group.who_can_start, linked_count=linked_count
        ),
    )
    await state.set_state(QuizStates.TG_GROUP_SETTINGS)
    await state.update_data(settings_chat_id=message.chat.id)


@router.callback_query(QuizStates.TG_GROUP_SETTINGS, F.data.startswith("tg:who:"))
async def set_who_can_start(cb: CallbackQuery, state: FSMContext) -> None:
    who = cb.data.split(":")[2]
    data = await state.get_data()
    chat_id = data.get("settings_chat_id")
    if not chat_id:
        await cb.answer()
        return
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(TelegramGroup)
            .where(TelegramGroup.chat_id == chat_id)
            .values(who_can_start=who)
        )
        await db.commit()
    group = await _get_or_create_group(chat_id, None)
    linked_count = len(json.loads(group.linked_quiz_ids or "[]"))
    await cb.message.edit_reply_markup(
        reply_markup=tg_group_settings_keyboard(who=who, linked_count=linked_count)
    )
    await cb.answer("✅ Saqlandi")


@router.callback_query(QuizStates.TG_GROUP_SETTINGS, F.data == "tg:save_settings")
async def save_settings(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.edit_text("✅ Sozlamalar saqlandi.")
    await cb.answer()


@router.callback_query(QuizStates.TG_GROUP_SETTINGS, F.data == "tg:manage_quizzes")
async def settings_manage_quizzes(
    cb: CallbackQuery, state: FSMContext, bot: Bot
) -> None:
    """Biriktirilgan quizlar ro'yxatini ko'rsatish."""
    chat_id = cb.message.chat.id
    data = await state.get_data()
    settings_chat_id = data.get("settings_chat_id", chat_id)

    group = await _get_or_create_group(settings_chat_id, None)
    linked_ids = json.loads(group.linked_quiz_ids or "[]")

    linked_quizzes = []
    for qid in linked_ids:
        try:
            q = await ai_engine_client().get_quiz(qid)
            q["id"] = qid
            linked_quizzes.append(q)
        except Exception:
            linked_quizzes.append(
                {"id": qid, "title": qid[:8] + "...", "total_questions": "?"}
            )

    await cb.message.edit_text(
        f"🔗 <b>Biriktirilgan quizlar ({len(linked_quizzes)} ta):</b>",
        reply_markup=tg_group_linked_quizzes_keyboard(linked_quizzes),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("tg:lq_remove:"))
async def lq_remove(cb: CallbackQuery, bot: Bot) -> None:
    """Biriktirilgan quizni ro'yxatdan olib tashlash."""
    chat_id = cb.message.chat.id
    if not await _is_chat_admin(bot, chat_id, cb.from_user.id):
        await cb.answer("⛔ Faqat admin!", show_alert=True)
        return

    quiz_id = cb.data.split(":", 2)[2]
    async with AsyncSessionLocal() as db_session:
        result = await db_session.execute(
            select(TelegramGroup).where(TelegramGroup.chat_id == chat_id)
        )
        grp = result.scalar_one_or_none()
        if grp:
            ids = json.loads(grp.linked_quiz_ids or "[]")
            ids = [i for i in ids if i != quiz_id]
            await db_session.execute(
                update(TelegramGroup)
                .where(TelegramGroup.chat_id == chat_id)
                .values(linked_quiz_ids=json.dumps(ids))
            )
            await db_session.commit()

    # Yangilangan ro'yxatni ko'rsatish
    group = await _get_or_create_group(chat_id, None)
    linked_ids = json.loads(group.linked_quiz_ids or "[]")
    linked_quizzes = []
    for qid in linked_ids:
        try:
            q = await ai_engine_client().get_quiz(qid)
            q["id"] = qid
            linked_quizzes.append(q)
        except Exception:
            linked_quizzes.append(
                {"id": qid, "title": qid[:8] + "...", "total_questions": "?"}
            )

    await cb.message.edit_text(
        f"🔗 <b>Biriktirilgan quizlar ({len(linked_quizzes)} ta):</b>",
        reply_markup=tg_group_linked_quizzes_keyboard(linked_quizzes),
    )
    await cb.answer("🗑 O'chirildi")


@router.callback_query(F.data == "tg:lq_add")
async def lq_add(cb: CallbackQuery, bot: Bot) -> None:
    """Yangi quiz qo'shish — admin quizlarini ko'rsatish."""
    chat_id = cb.message.chat.id
    if not await _is_chat_admin(bot, chat_id, cb.from_user.id):
        await cb.answer("⛔ Faqat admin!", show_alert=True)
        return

    try:
        data = await ai_engine_client().get_quizzes(user_id=cb.from_user.id)
        quizzes = data.get("quizzes", []) if isinstance(data, dict) else (data or [])
    except Exception:
        quizzes = []

    if not quizzes:
        await cb.answer("Sizda quiz yo'q.", show_alert=True)
        return

    _group_sessions[chat_id] = {"phase": "selecting", "started_by": cb.from_user.id}
    await cb.message.edit_text(
        "📋 <b>Qo'shish uchun quiz tanlang:</b>",
        reply_markup=tg_group_quiz_select_keyboard(quizzes),
    )
    await cb.answer()


@router.callback_query(F.data == "tg:lq_back")
async def lq_back(cb: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    """Quizlar ro'yxatidan settings ga qaytish."""
    chat_id = cb.message.chat.id
    group = await _get_or_create_group(chat_id, None)
    linked_count = len(json.loads(group.linked_quiz_ids or "[]"))
    await state.set_state(QuizStates.TG_GROUP_SETTINGS)
    await state.update_data(settings_chat_id=chat_id)
    await cb.message.edit_text(
        "⚙️ <b>Guruh sozlamalari:</b>",
        reply_markup=tg_group_settings_keyboard(
            who=group.who_can_start, linked_count=linked_count
        ),
    )
    await cb.answer()


# ── §14.3  /quiz — guruhda quiz boshlash ─────────────────────────────────────


async def _launch_voting(
    bot: Bot,
    chat_id: int,
    quiz_id: str,
    user_id: int,
    group: TelegramGroup,
    reply_to_msg_id: int | None = None,
) -> None:
    """Voting yoki to'g'ridan-to'g'ri quiz boshlash. Session allaqachon yo'q deb faraz qilinadi."""
    try:
        quiz = await ai_engine_client().get_quiz(quiz_id)
        quiz_name = quiz.get("title", quiz.get("name", "Quiz"))
        question_count = quiz.get("total_questions", 10)
    except Exception:
        await bot.send_message(
            chat_id, "❌ Quiz topilmadi. Admin yangi quiz biriktirsin."
        )
        return

    time_per_q = 30

    _group_sessions[chat_id] = {
        "phase": "voting",
        "quiz_id": quiz_id,
        "quiz_name": quiz_name,
        "set_number": 1,
        "question_count": question_count,
        "time_per_q": time_per_q,
        "min_voters": group.min_voters,
        "voters": set(),
        "started_by": user_id,
        "scores": {},
    }

    sent = await bot.send_message(
        chat_id,
        f"🗳 <b>Quiz boshlashga ovoz bering!</b>\n\n"
        f"📋 <b>{quiz_name}</b> ({question_count} savol)\n"
        f"⏱ Har savol: {time_per_q} soniya\n\n"
        f"Boshlash uchun kamida {group.min_voters} kishi kerak.\n"
        f"⏳ Kutish: {group.voting_timeout} soniya\n\n"
        f"✅ Tayyorman: 0 kishi",
        reply_markup=voting_keyboard(msg_id=0, voter_count=0),
    )
    _group_sessions[chat_id]["vote_msg_id"] = sent.message_id
    await bot.edit_message_reply_markup(
        chat_id=chat_id,
        message_id=sent.message_id,
        reply_markup=voting_keyboard(msg_id=sent.message_id, voter_count=0),
    )
    asyncio.create_task(
        _voting_timeout(bot, chat_id, sent.message_id, group.voting_timeout)
    )


@router.message(Command("quiz"), F.chat.type.in_({"group", "supergroup"}))
async def group_quiz_command(message: Message, state: FSMContext, bot: Bot) -> None:
    group = await _get_or_create_group(message.chat.id, message.chat.title)
    chat_id = message.chat.id
    user_id = message.from_user.id
    is_admin = await _is_chat_admin(bot, chat_id, user_id)

    # Ruxsat tekshiruvi
    if group.who_can_start == "admin" and not is_admin:
        await message.reply("⛔ Bu guruhda quizni faqat admin boshlaya oladi.")
        return

    # Faol session tekshiruvi
    if chat_id in _group_sessions:
        phase = _group_sessions[chat_id].get("phase", "")
        if phase == "voting":
            await message.reply(
                "⚠️ Ovoz berish davom etmoqda. Qatnashing yoki tugashini kuting."
            )
        else:
            await message.reply(
                "⚠️ Quiz davom etmoqda! To'xtatish uchun /stop yuboring."
            )
        return

    linked_ids = json.loads(group.linked_quiz_ids or "[]")

    if len(linked_ids) == 1:
        # Bitta quiz — darhol boshlash
        await _launch_voting(bot, chat_id, linked_ids[0], user_id, group)
        return

    if len(linked_ids) > 1:
        # Bir nechta quiz — qaysi birini boshlash?
        try:
            quizzes = []
            for qid in linked_ids:
                q = await ai_engine_client().get_quiz(qid)
                q["id"] = qid
                quizzes.append(q)
        except Exception:
            quizzes = [
                {"id": qid, "title": f"Quiz {i+1}", "total_questions": "?"}
                for i, qid in enumerate(linked_ids)
            ]

        _group_sessions[chat_id] = {"phase": "selecting", "started_by": user_id}
        await message.reply(
            "📋 <b>Qaysi quizni boshlash kerak?</b>",
            reply_markup=tg_group_quiz_start_keyboard(quizzes),
        )
        return

    # Biriktirilgan quiz yo'q
    if is_admin:
        try:
            data = await ai_engine_client().get_quizzes(user_id=user_id)
            quizzes = (
                data.get("quizzes", []) if isinstance(data, dict) else (data or [])
            )
        except Exception:
            quizzes = []

        if not quizzes:
            await message.reply(
                "📂 Sizda hali quiz yo'q.\n\n" "Avval botga fayl yuborib quiz yarating."
            )
            return

        _group_sessions[chat_id] = {"phase": "selecting", "started_by": user_id}
        await message.reply(
            "📋 <b>Guruhga qaysi quizni biriktirish kerak?</b>\n\n"
            "<i>Tanlangan quiz guruhga biriktiriladi.</i>",
            reply_markup=tg_group_quiz_select_keyboard(quizzes),
        )
    else:
        await message.reply(
            "ℹ️ Guruhga hali quiz biriktirilmagan.\n\n"
            "Admin /settings orqali quizni biriktirishi kerak."
        )


@router.message(Command("stop"), F.chat.type.in_({"group", "supergroup"}))
async def group_stop_quiz(message: Message, bot: Bot) -> None:
    """
    Har qanday user /stop yubora oladi → stop-voting.
    Admin darhol to'xtatadi.
    """
    chat_id = message.chat.id
    user_id = message.from_user.id
    session = _group_sessions.get(chat_id)

    if not session or session.get("phase") not in ("voting", "playing"):
        await message.reply("⚠️ Hozir faol quiz yo'q.")
        return

    is_admin = await _is_chat_admin(bot, chat_id, user_id)

    # Admin darhol to'xtatadi
    if is_admin:
        _group_sessions.pop(chat_id, None)
        await message.reply("⏹ Quiz admin tomonidan to'xtatildi.")
        return

    # Oddiy user — stop-voting
    group = await _get_or_create_group(chat_id, message.chat.title)
    stop_min = group.stop_min_voters
    stop_voters: set = session.setdefault("stop_voters", set())

    if user_id in stop_voters:
        await message.reply(
            f"Siz allaqachon ovoz berdingiz. ({len(stop_voters)}/{stop_min})"
        )
        return

    stop_voters.add(user_id)

    if len(stop_voters) >= stop_min:
        _group_sessions.pop(chat_id, None)
        await message.reply(f"⏹ <b>{len(stop_voters)} ovoz</b> bilan quiz to'xtatildi!")
    else:
        remaining = stop_min - len(stop_voters)
        await message.reply(
            f"🗳 To'xtatish ovozi: <b>{len(stop_voters)}/{stop_min}</b>\n"
            f"Yana {remaining} ta /stop kerak."
        )


@router.callback_query(F.data.startswith("tg:gselect:"))
async def group_select_quiz(cb: CallbackQuery, bot: Bot) -> None:
    """Admin guruhga yangi quiz biriktiradi (ro'yxatga qo'shadi)."""
    chat_id = cb.message.chat.id
    session = _group_sessions.get(chat_id)

    if not session or session.get("phase") != "selecting":
        await cb.answer("Tanlash vaqti o'tib ketdi.", show_alert=True)
        return

    started_by = session.get("started_by")
    if cb.from_user.id != started_by and not await _is_chat_admin(
        bot, chat_id, cb.from_user.id
    ):
        await cb.answer("⛔ Faqat admin tanlashi mumkin!", show_alert=True)
        return

    quiz_id = cb.data.split(":", 2)[2]

    # Ro'yxatga qo'shish (duplicate yo'q)
    async with AsyncSessionLocal() as db_session:
        result = await db_session.execute(
            select(TelegramGroup).where(TelegramGroup.chat_id == chat_id)
        )
        grp = result.scalar_one_or_none()
        if grp:
            ids = json.loads(grp.linked_quiz_ids or "[]")
            if quiz_id not in ids:
                ids.append(quiz_id)
                await db_session.execute(
                    update(TelegramGroup)
                    .where(TelegramGroup.chat_id == chat_id)
                    .values(linked_quiz_ids=json.dumps(ids))
                )
                await db_session.commit()

    _group_sessions.pop(chat_id, None)
    await cb.message.edit_text("✅ Quiz guruhga biriktirildi. Voting boshlanmoqda...")

    group = await _get_or_create_group(chat_id, None)
    await _launch_voting(bot, chat_id, quiz_id, cb.from_user.id, group)
    await cb.answer()


@router.callback_query(F.data.startswith("tg:gstart:"))
async def group_start_linked_quiz(cb: CallbackQuery, bot: Bot) -> None:
    """Biriktirilgan quizlar orasidan birini boshlash."""
    chat_id = cb.message.chat.id
    session = _group_sessions.get(chat_id)

    if not session or session.get("phase") != "selecting":
        await cb.answer("Tanlash vaqti o'tib ketdi.", show_alert=True)
        return

    if not await _is_chat_admin(bot, chat_id, cb.from_user.id):
        group = await _get_or_create_group(chat_id, None)
        if group.who_can_start == "admin":
            await cb.answer("⛔ Faqat admin boshlaya oladi!", show_alert=True)
            return

    quiz_id = cb.data.split(":", 2)[2]
    _group_sessions.pop(chat_id, None)
    await cb.message.edit_text("🚀 Voting boshlanmoqda...")

    group = await _get_or_create_group(chat_id, None)
    await _launch_voting(bot, chat_id, quiz_id, cb.from_user.id, group)
    await cb.answer()


@router.callback_query(F.data == "tg:cancel_select")
async def group_cancel_select(cb: CallbackQuery, bot: Bot) -> None:
    chat_id = cb.message.chat.id
    session = _group_sessions.get(chat_id)

    if session and session.get("phase") == "selecting":
        started_by = session.get("started_by")
        if cb.from_user.id != started_by and not await _is_chat_admin(
            bot, chat_id, cb.from_user.id
        ):
            await cb.answer("⛔ Faqat admin bekor qilishi mumkin!", show_alert=True)
            return
        _group_sessions.pop(chat_id, None)

    await cb.message.edit_text("❌ Quiz tanlash bekor qilindi.")
    await cb.answer()


@router.callback_query(F.data == "tg:cancel_vote")
async def cancel_voting(cb: CallbackQuery, bot: Bot) -> None:
    """Admin voting ni bekor qiladi."""
    chat_id = cb.message.chat.id
    session = _group_sessions.get(chat_id)

    if not session or session.get("phase") != "voting":
        await cb.answer()
        return

    if not await _is_chat_admin(bot, chat_id, cb.from_user.id):
        await cb.answer("⛔ Faqat admin bekor qila oladi!", show_alert=True)
        return

    _group_sessions.pop(chat_id, None)
    await cb.message.edit_text("❌ Voting admin tomonidan bekor qilindi.")
    await cb.answer()


# ── Voting timeout ────────────────────────────────────────────────────────────


async def _voting_timeout(
    bot: Bot, chat_id: int, vote_msg_id: int, timeout: int
) -> None:
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

    # Haqiqiy savollarni ai-engine dan olish
    quiz_id = session.get("quiz_id")
    set_number = session.get("set_number", 1)
    questions: list[dict] = []

    if quiz_id:
        try:
            questions = await ai_engine_client().get_questions(quiz_id, set_number)
        except Exception:
            logger.warning(
                "group quiz: questions olinmadi quiz_id=%s, demo ishlatilmoqda", quiz_id
            )

    if not questions:
        questions = _DEMO_QUESTIONS  # type: ignore[assignment]

    q_count = min(session.get("question_count", len(questions)), len(questions))
    session["question_count"] = q_count
    session["questions"] = questions[:q_count]
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

    questions = session.get("questions", _DEMO_QUESTIONS)
    raw_q = questions[idx % len(questions)]
    time_limit = session.get("time_per_q", 30)

    # Savollar ikkala formatda kelishi mumkin: ai-engine va demo
    if "question_text" in raw_q:
        q_text = raw_q["question_text"]
        options = raw_q.get("options", [])
        correct = raw_q.get("correct_indices", [0])[0]
    else:
        q_text = raw_q["question"]
        options = raw_q["options"]
        correct = raw_q["correct"]

    # Telegram cheklovi: savol max 300, variant max 100 belgi
    poll_question = f"❓ {idx + 1}/{q_count}: {q_text}"[:300]
    poll_options = [str(o)[:100] for o in options]

    sent = await bot.send_poll(
        chat_id=chat_id,
        question=poll_question,
        options=poll_options,
        type="quiz",
        correct_option_id=correct,
        is_anonymous=False,
        open_period=time_limit,
    )

    session["poll_ids"][sent.poll.id] = idx
    session["current_q"] = idx + 1

    # Keyingi savolga o'tish — poll muddati + 1 soniya
    asyncio.create_task(_wait_and_next(bot, chat_id, time_limit + 1))


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
    questions = session.get("questions", _DEMO_QUESTIONS)
    raw_q = questions[q_idx % len(questions)]
    if "correct_indices" in raw_q:
        correct_idx = raw_q["correct_indices"][0]
    else:
        correct_idx = raw_q["correct"]

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
        lines.append(f"{medal} {info['name']} — {info['correct']}/{q_count}")
        total_correct += info["correct"]

    avg_pct = int(total_correct / (len(ranked) * q_count) * 100) if ranked else 0
    participant_count = len(ranked)

    text = (
        "🏁 <b>Quiz natijasi:</b>\n\n"
        + "\n".join(lines)
        + f"\n\n👥 Qatnashganlar: {participant_count} kishi\n"
        f"📊 O'rtacha: {avg_pct}%"
    )

    await bot.send_message(chat_id, text, reply_markup=group_result_keyboard())


@router.callback_query(F.data == "tg:detail")
async def group_detail_noop(cb: CallbackQuery) -> None:
    """Batafsil natija — hozircha natija xabarida ko'rinadi."""
    await cb.answer("Natija yuqorida ko'rsatilgan.", show_alert=True)


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
    """Guruhda yana o'ynash — biriktirilgan quiz bo'lsa darhol, bo'lmasa tanlash."""
    chat_id = cb.message.chat.id
    if not await _is_chat_admin(bot, chat_id, cb.from_user.id):
        await cb.answer("⛔ Faqat admin qayta boshlaya oladi!", show_alert=True)
        return

    if chat_id in _group_sessions:
        await cb.answer("Quiz hozir ham davom etmoqda!", show_alert=True)
        return

    group = await _get_or_create_group(chat_id, None)
    linked_ids = json.loads(group.linked_quiz_ids or "[]")

    if len(linked_ids) == 1:
        await cb.message.edit_text("🔄 Qayta boshlanmoqda...")
        await _launch_voting(bot, chat_id, linked_ids[0], cb.from_user.id, group)
        await cb.answer()
        return

    if len(linked_ids) > 1:
        try:
            quizzes = []
            for qid in linked_ids:
                q = await ai_engine_client().get_quiz(qid)
                q["id"] = qid
                quizzes.append(q)
        except Exception:
            quizzes = [
                {"id": qid, "title": f"Quiz {i+1}", "total_questions": "?"}
                for i, qid in enumerate(linked_ids)
            ]
        _group_sessions[chat_id] = {"phase": "selecting", "started_by": cb.from_user.id}
        await cb.message.edit_text(
            "📋 <b>Qaysi quizni boshlash kerak?</b>",
            reply_markup=tg_group_quiz_start_keyboard(quizzes),
        )
        await cb.answer()
        return

    # Biriktirilgan quiz yo'q — admin tanlaydi
    try:
        data = await ai_engine_client().get_quizzes(user_id=cb.from_user.id)
        quizzes = data.get("quizzes", []) if isinstance(data, dict) else (data or [])
    except Exception:
        quizzes = []

    if not quizzes:
        await cb.answer("Sizda quiz yo'q.", show_alert=True)
        return

    _group_sessions[chat_id] = {
        "phase": "selecting",
        "started_by": cb.from_user.id,
    }

    await cb.message.edit_text(
        "📋 <b>Qaysi quizni boshlash kerak?</b>",
        reply_markup=tg_group_quiz_select_keyboard(quizzes),
    )
    await cb.answer()
