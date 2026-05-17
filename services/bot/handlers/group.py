"""
Quiz Guruh (Kanal Konsepti) — BOT_UX.md §13.

Quiz Guruh = foydalanuvchining virtual quiz kanali (Telegram guruh emas).
Maqsad: auditoriya yig'ish, obunachilarga yangi quiz xabari yuborish.

Handler oqimlari:
  §13.1 — Guruh yaratish (FSM: name → desc → tags → create)
  §13.2 — Guruhni boshqarish (attach quiz, broadcast, stats, share)
  §13.3 — Obuna bo'lish (boshqa user link orqali)
  §13.4 — Obunalarim (subscribe qilingan guruhlar ro'yxati)
"""
import logging
import re
import uuid

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select, func

from db import AsyncSessionLocal
from db.models import QuizGroup, QuizGroupSubscriber, User
from fsm.states import QuizStates
from keyboards.inline import quiz_group_keyboard, quiz_group_list_keyboard, subscribe_group_keyboard

logger = logging.getLogger(__name__)
router = Router()


def _slug_from_name(name: str) -> str:
    """'DTM Tayyorgarlik 2025' → 'dtm-tayyorgarlik-2025-xxxx'"""
    slug = re.sub(r"[^a-zA-Z0-9\u0400-\u04FF\s]", "", name.lower())
    slug = re.sub(r"\s+", "-", slug.strip())[:40]
    short_id = str(uuid.uuid4())[:8]
    return f"{slug}-{short_id}"


async def _get_user_uuid(session, telegram_id: int) -> uuid.UUID | None:
    result = await session.execute(select(User.id).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


# ─────────────────────── Guruh ro'yxati ───────────────────────

@router.callback_query(F.data == "qg:list")
async def list_my_groups(cb: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user_id = await _get_user_uuid(session, cb.from_user.id)
        if not user_id:
            await cb.answer("Avval /start bosing", show_alert=True)
            return

        result = await session.execute(
            select(QuizGroup)
            .where(QuizGroup.owner_id == user_id)
            .where(QuizGroup.is_active == True)
            .order_by(QuizGroup.created_at.desc())
        )
        groups = result.scalars().all()

    if not groups:
        await cb.message.edit_text(
            "📌 Sizda hali quiz guruh yo'q.\n\n"
            "Guruh yaratib, obunachilarga yangi quizlar haqida xabar yuboring!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Yangi guruh yaratish", callback_data="qg:create")],
                [InlineKeyboardButton(text="🏠 Menyu", callback_data="qb:menu")],
            ]),
        )
        await cb.answer()
        return

    groups_data = [
        {"id": str(g.id), "name": g.name, "subscriber_count": g.subscriber_count}
        for g in groups
    ]
    await cb.message.edit_text(
        "📌 Sizning quiz guruhlaringiz:",
        reply_markup=quiz_group_list_keyboard(groups_data),
    )
    await cb.answer()


# ─────────────────────── Guruh yaratish ───────────────────────

@router.callback_query(F.data == "qg:create")
async def start_create_group(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(QuizStates.QUIZ_GROUP_CREATE_NAME)
    await cb.message.edit_text(
        "📌 Yangi quiz guruh yaratish\n\n"
        "Guruh nomini kiriting (masalan: \"DTM Tayyorgarlik 2025\"):"
    )
    await cb.answer()


@router.message(QuizStates.QUIZ_GROUP_CREATE_NAME)
async def receive_group_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("❌ Nom kamida 3 ta harf bo'lishi kerak.")
        return
    await state.update_data(group_name=name)
    await state.set_state(QuizStates.QUIZ_GROUP_CREATE_DESC)
    await message.answer(
        f"✅ Nom: <b>{name}</b>\n\n"
        "Qisqacha tavsif kiriting (ixtiyoriy, «o'tkazib yuborish» yozing o'tkazish uchun):"
    )


@router.message(QuizStates.QUIZ_GROUP_CREATE_DESC)
async def receive_group_desc(message: Message, state: FSMContext) -> None:
    desc = message.text.strip()
    if desc.lower() in ("o'tkazib yuborish", "skip", "пропустить"):
        desc = ""
    await state.update_data(group_desc=desc)
    await state.set_state(QuizStates.QUIZ_GROUP_CREATE_TAGS)
    await message.answer(
        "Teglarni kiriting (masalan: #dtm #biologiya #abiturient)\n"
        "Yoki «o'tkazib yuborish» yozing:"
    )


@router.message(QuizStates.QUIZ_GROUP_CREATE_TAGS)
async def receive_group_tags(message: Message, state: FSMContext) -> None:
    tags_text = message.text.strip()
    if tags_text.lower() in ("o'tkazib yuborish", "skip", "пропустить"):
        tags_text = ""

    data = await state.get_data()
    name = data.get("group_name", "")
    desc = data.get("group_desc", "")
    slug = _slug_from_name(name)

    async with AsyncSessionLocal() as session:
        user_id = await _get_user_uuid(session, message.from_user.id)
        if not user_id:
            await message.answer("❌ Foydalanuvchi topilmadi. /start bosing.")
            await state.clear()
            return

        group = QuizGroup(
            owner_id=user_id,
            name=name,
            description=desc or None,
            slug=slug,
        )
        session.add(group)
        await session.commit()
        await session.refresh(group)
        group_id = group.id

    await state.clear()

    bot_username = (await message.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=g_{slug}"

    await message.answer(
        f"✅ Quiz guruh yaratildi!\n\n"
        f"📌 <b>{name}</b>\n"
        f"🔗 Link: {link}\n\n"
        "Endi quiz yaratib, shu guruhga biriktiring!",
        reply_markup=quiz_group_keyboard(str(group_id)),
    )


# ─────────────────────── Guruh ko'rish ───────────────────────

@router.callback_query(F.data.startswith("qg:view:"))
async def view_group(cb: CallbackQuery, state: FSMContext) -> None:
    group_id = cb.data.split(":")[2]

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(QuizGroup).where(QuizGroup.id == uuid.UUID(group_id))
        )
        group = result.scalar_one_or_none()

        if not group:
            await cb.answer("Guruh topilmadi", show_alert=True)
            return

        # Owner tekshirish
        user_result = await session.execute(
            select(User.id).where(User.telegram_id == cb.from_user.id)
        )
        user_uuid = user_result.scalar_one_or_none()
        is_owner = group.owner_id == user_uuid

    text = (
        f"📌 <b>{group.name}</b>\n"
        f"👥 {group.subscriber_count} obunachi\n"
        f"📚 {group.quiz_count} to'plam\n"
    )
    if group.description:
        text += f"\n{group.description}\n"

    if is_owner:
        await cb.message.edit_text(text, reply_markup=quiz_group_keyboard(group_id))
    else:
        # Obuna bo'lganligini tekshirish
        async with AsyncSessionLocal() as session:
            sub_result = await session.execute(
                select(QuizGroupSubscriber).where(
                    QuizGroupSubscriber.quiz_group_id == uuid.UUID(group_id),
                    QuizGroupSubscriber.user_id == user_uuid,
                )
            )
            is_subscribed = sub_result.scalar_one_or_none() is not None

        await cb.message.edit_text(
            text, reply_markup=subscribe_group_keyboard(group_id, is_subscribed)
        )
    await cb.answer()


# ─────────────────────── Obuna bo'lish / chiqish ───────────────────────

@router.callback_query(F.data.startswith("qg:sub:"))
async def subscribe_group(cb: CallbackQuery, state: FSMContext) -> None:
    group_id = cb.data.split(":")[2]

    async with AsyncSessionLocal() as session:
        user_id = await _get_user_uuid(session, cb.from_user.id)
        if not user_id:
            await cb.answer("Avval /start bosing", show_alert=True)
            return

        # Allaqachon obuna?
        existing = await session.execute(
            select(QuizGroupSubscriber).where(
                QuizGroupSubscriber.quiz_group_id == uuid.UUID(group_id),
                QuizGroupSubscriber.user_id == user_id,
            )
        )
        if existing.scalar_one_or_none():
            await cb.answer("Siz allaqachon obunasiz!", show_alert=True)
            return

        sub = QuizGroupSubscriber(
            quiz_group_id=uuid.UUID(group_id),
            user_id=user_id,
        )
        session.add(sub)

        # subscriber_count +1
        group_result = await session.execute(
            select(QuizGroup).where(QuizGroup.id == uuid.UUID(group_id))
        )
        group = group_result.scalar_one_or_none()
        if group:
            group.subscriber_count = (group.subscriber_count or 0) + 1

        await session.commit()

    await cb.answer("✅ Obuna bo'ldingiz!", show_alert=True)
    await cb.message.edit_reply_markup(
        reply_markup=subscribe_group_keyboard(group_id, is_subscribed=True)
    )


@router.callback_query(F.data.startswith("qg:unsub:"))
async def unsubscribe_group(cb: CallbackQuery, state: FSMContext) -> None:
    group_id = cb.data.split(":")[2]

    async with AsyncSessionLocal() as session:
        user_id = await _get_user_uuid(session, cb.from_user.id)
        if not user_id:
            await cb.answer("Avval /start bosing", show_alert=True)
            return

        result = await session.execute(
            select(QuizGroupSubscriber).where(
                QuizGroupSubscriber.quiz_group_id == uuid.UUID(group_id),
                QuizGroupSubscriber.user_id == user_id,
            )
        )
        sub = result.scalar_one_or_none()
        if sub:
            await session.delete(sub)
            # subscriber_count -1
            group_result = await session.execute(
                select(QuizGroup).where(QuizGroup.id == uuid.UUID(group_id))
            )
            group = group_result.scalar_one_or_none()
            if group and group.subscriber_count > 0:
                group.subscriber_count -= 1
            await session.commit()

    await cb.answer("✅ Obunadan chiqdingiz.", show_alert=True)
    await cb.message.edit_reply_markup(
        reply_markup=subscribe_group_keyboard(group_id, is_subscribed=False)
    )


# ─────────────────────── /start?start=g_slug handler ───────────────────────

@router.message(CommandStart(deep_link=True, magic=F.args.startswith("g_")))
async def open_group_link(message: Message, state: FSMContext) -> None:
    """Guruh link orqali kirish: /start g_<slug>"""
    slug = message.args[2:]  # "g_" ni olib tashlash

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(QuizGroup).where(QuizGroup.slug == slug).where(QuizGroup.is_active == True)
        )
        group = result.scalar_one_or_none()

    if not group:
        await message.answer("❌ Quiz guruh topilmadi yoki o'chirilgan.")
        return

    # Obuna tekshirish
    async with AsyncSessionLocal() as session:
        user_id = await _get_user_uuid(session, message.from_user.id)
        is_subscribed = False
        if user_id:
            sub_result = await session.execute(
                select(QuizGroupSubscriber).where(
                    QuizGroupSubscriber.quiz_group_id == group.id,
                    QuizGroupSubscriber.user_id == user_id,
                )
            )
            is_subscribed = sub_result.scalar_one_or_none() is not None

    await message.answer(
        f"📌 <b>{group.name}</b>\n"
        f"👥 {group.subscriber_count} obunachi\n"
        f"📚 {group.quiz_count} to'plam\n"
        + (f"\n{group.description}" if group.description else ""),
        reply_markup=subscribe_group_keyboard(str(group.id), is_subscribed),
    )


# ─────────────────────── Broadcast ───────────────────────

@router.callback_query(F.data.startswith("qg:broadcast:"))
async def start_broadcast(cb: CallbackQuery, state: FSMContext) -> None:
    group_id = cb.data.split(":")[2]
    await state.set_state(QuizStates.QUIZ_GROUP_BROADCAST)
    await state.update_data(broadcast_group_id=group_id)
    await cb.message.answer(
        "📢 Barcha obunachilarga yuboriladigan xabarni kiriting:"
    )
    await cb.answer()


@router.message(QuizStates.QUIZ_GROUP_BROADCAST)
async def send_broadcast(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    group_id = data.get("broadcast_group_id")
    if not group_id:
        await state.clear()
        return

    # Obunachilarn telegram_id larini olish
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User.telegram_id)
            .join(QuizGroupSubscriber, QuizGroupSubscriber.user_id == User.id)
            .where(QuizGroupSubscriber.quiz_group_id == uuid.UUID(group_id))
        )
        telegram_ids = [row[0] for row in result.fetchall()]

    sent = 0
    failed = 0
    for tg_id in telegram_ids:
        try:
            await message.bot.send_message(tg_id, message.text)
            sent += 1
        except Exception:
            failed += 1

    await state.clear()
    await message.answer(
        f"📢 Broadcast yuborildi!\n"
        f"✅ {sent} ta obunachiga yetdi\n"
        f"❌ {failed} ta muvaffaqiyatsiz"
    )


# ─────────────────────── Statistika ───────────────────────

@router.callback_query(F.data.startswith("qg:stats:"))
async def group_stats(cb: CallbackQuery, state: FSMContext) -> None:
    group_id = cb.data.split(":")[2]

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(QuizGroup).where(QuizGroup.id == uuid.UUID(group_id))
        )
        group = result.scalar_one_or_none()

    if not group:
        await cb.answer("Guruh topilmadi", show_alert=True)
        return

    await cb.message.answer(
        f"📊 <b>{group.name}</b> statistikasi:\n\n"
        f"👥 Obunachlar: {group.subscriber_count}\n"
        f"📚 To'plamlar: {group.quiz_count}\n"
        f"📅 Yaratilgan: {group.created_at.strftime('%d.%m.%Y') if group.created_at else '—'}\n",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀ Orqaga", callback_data=f"qg:view:{group_id}")]
        ]),
    )
    await cb.answer()


# ─────────────────────── Link ulashish ───────────────────────

@router.callback_query(F.data.startswith("qg:share:"))
async def share_group_link(cb: CallbackQuery, state: FSMContext) -> None:
    group_id = cb.data.split(":")[2]

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(QuizGroup.slug, QuizGroup.name).where(QuizGroup.id == uuid.UUID(group_id))
        )
        row = result.one_or_none()

    if not row:
        await cb.answer("Guruh topilmadi", show_alert=True)
        return

    slug, name = row
    bot_username = (await cb.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=g_{slug}"

    await cb.message.answer(
        f"📤 <b>{name}</b> guruh linki:\n\n"
        f"<code>{link}</code>\n\n"
        "Do'stlaringizga yuboring — obuna bo'lsinlar!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Ulashish", switch_inline_query=link)],
            [InlineKeyboardButton(text="◀ Orqaga", callback_data=f"qg:view:{group_id}")],
        ]),
    )
    await cb.answer()
