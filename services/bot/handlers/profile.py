"""Profil, reyting va referal handlerlari."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.inline import (
    profile_keyboard, leaderboard_tabs_keyboard,
    referral_keyboard, premium_plans_keyboard, payment_keyboard,
)
from utils.api import game_client, subscription_client

router = Router()

LEVEL_ICONS = {
    "beginner": "🌱",
    "learner": "📗",
    "expert": "📘",
    "master": "📙",
    "professor": "📕",
    "academic": "👑",
}

LEVEL_NAMES_UZ = {
    "beginner": "Yangi",
    "learner": "O'rganuvchi",
    "expert": "Bilimdon",
    "master": "Ustoz",
    "professor": "Professor",
    "academic": "Akademik",
}


# ─────────────────────────── Profil ───────────────────────────

@router.message(Command("profile"))
@router.message(F.text.in_({"👤 Profil", "👤 Profile", "👤 Профиль"}))
@router.callback_query(F.data == "prof:view")
async def show_profile(event, state=None) -> None:
    """Foydalanuvchi profili — real statslar bilan"""
    if isinstance(event, CallbackQuery):
        user = event.from_user
        send = event.message.edit_text
        answer = event.answer
    else:
        user = event.from_user
        send = event.answer
        answer = None

    # Game servisdan stats olish
    stats = {}
    try:
        stats = await game_client().get_user_stats(user.id)
    except Exception:
        pass

    # Subscription servisdan plan olish
    plan = "free"
    expires_at = None
    try:
        sub = await subscription_client().get_plan(user.id)
        plan = sub.get("plan", "free")
        expires_at = sub.get("expires_at")
    except Exception:
        pass

    level = stats.get("level", "beginner")
    level_icon = LEVEL_ICONS.get(level, "🌱")
    level_name = LEVEL_NAMES_UZ.get(level, "Yangi")
    total_xp = stats.get("total_xp", 0)
    streak = stats.get("current_streak", 0)
    total_games = stats.get("total_games", 0)
    accuracy = stats.get("accuracy", 0)
    total_correct = stats.get("total_correct", 0)
    total_wrong = stats.get("total_wrong", 0)
    total_q = total_correct + total_wrong

    plan_text = "💎 Premium" if plan == "premium" else ("🏢 Business" if plan == "business" else "🆓 Free")
    if expires_at:
        plan_text += f" (→ {expires_at[:10]})"

    text = (
        f"👤 <b>{user.full_name}</b>\n"
        f"{level_icon} {level_name} ({total_xp} XP)\n"
        f"🔥 Streak: {streak} kun\n\n"
        f"📊 Statistika:\n"
        f"├── O'ynagan: {total_games} quiz\n"
        f"├── To'g'ri: {accuracy:.0f}%\n"
        f"└── Jami savollar: {total_q}\n\n"
        f"{plan_text}"
    )

    try:
        await send(text, reply_markup=profile_keyboard())
    except Exception:
        if isinstance(event, Message):
            await event.answer(text, reply_markup=profile_keyboard())

    if answer:
        await answer()


@router.callback_query(F.data == "prof:detail")
async def show_detail_stats(cb: CallbackQuery) -> None:
    """Batafsil statistika"""
    try:
        stats = await game_client().get_user_stats(cb.from_user.id)
    except Exception:
        stats = {}

    level = stats.get("level", "beginner")
    text = (
        f"📊 <b>Batafsil statistika</b>\n\n"
        f"🎮 Jami o'yinlar: {stats.get('total_games', 0)}\n"
        f"✅ To'g'ri: {stats.get('total_correct', 0)}\n"
        f"❌ Noto'g'ri: {stats.get('total_wrong', 0)}\n"
        f"🎯 Aniqlik: {stats.get('accuracy', 0):.1f}%\n\n"
        f"⭐ Jami XP: {stats.get('total_xp', 0)}\n"
        f"🏆 Daraja: {LEVEL_ICONS.get(level, '🌱')} {LEVEL_NAMES_UZ.get(level, 'Yangi')}\n\n"
        f"🔥 Hozirgi streak: {stats.get('current_streak', 0)} kun\n"
        f"📈 Eng uzun streak: {stats.get('longest_streak', 0)} kun"
    )

    await cb.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀ Orqaga", callback_data="prof:view")]
        ]),
    )
    await cb.answer()


# ─────────────────────────── Premium ───────────────────────────

@router.message(F.text.in_({"💎 Obuna", "💎 Premium"}))
@router.callback_query(F.data == "prof:premium")
async def show_premium(event) -> None:
    text = (
        "💎 <b>Premium rejalar</b>\n\n"
        "📅 <b>Oylik</b> — 29 000 so'm\n"
        "📆 <b>Yillik</b> — 249 000 so'm (29% tejash)\n\n"
        "Premium bilan:\n"
        "• Cheksiz fayl yuklash\n"
        "• Guruhga ulashish\n"
        "• Quiz doim saqlanadi\n"
        "• Batafsil statistika\n\n"
        "Yoki 3 ta do'st taklif qiling = 9 kun bepul!"
    )

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=premium_plans_keyboard())
        await event.answer()
    else:
        await event.answer(text, reply_markup=premium_plans_keyboard())


@router.callback_query(F.data.in_({"pay:monthly", "pay:yearly"}))
async def show_payment_options(cb: CallbackQuery) -> None:
    period = "Oylik" if cb.data == "pay:monthly" else "Yillik"
    price = "29 000 so'm" if cb.data == "pay:monthly" else "249 000 so'm"
    await cb.message.edit_text(
        f"💳 <b>{period} — {price}</b>\n\n"
        "To'lov usulini tanlang:",
        reply_markup=payment_keyboard(),
    )
    await cb.answer()


@router.callback_query(F.data == "pay:stars")
async def pay_with_stars(cb: CallbackQuery) -> None:
    await cb.answer(
        "⭐ Telegram Stars to'lov tez orada qo'shiladi!",
        show_alert=True,
    )


@router.callback_query(F.data == "pay:close")
async def close_payment(cb: CallbackQuery) -> None:
    await cb.message.delete()
    await cb.answer()


# ─────────────────────────── Reyting ───────────────────────────

@router.message(Command("top"))
@router.message(F.text.in_({"🏆 Reyting", "🏆 Rating", "🏆 Рейтинг"}))
async def show_leaderboard(message: Message) -> None:
    await _send_leaderboard(message, "all")


@router.callback_query(F.data.startswith("lb:tab:"))
async def leaderboard_tab(cb: CallbackQuery) -> None:
    tab = cb.data.split(":")[2]
    await _send_leaderboard(cb.message, tab, edit=True)
    await cb.answer()


async def _send_leaderboard(message: Message, period: str, edit: bool = False) -> None:
    period_map = {
        "today": ("daily", None),
        "week": ("weekly", None),
        "month": ("monthly", None),
        "all": ("alltime", None),
    }
    api_period, _ = period_map.get(period, ("alltime", None))

    try:
        data = await game_client().get_leaderboard(period=api_period, limit=10)
        entries = data.get("entries", [])
    except Exception:
        entries = []

    if not entries:
        text = (
            "🏆 <b>Reyting</b>\n\n"
            "Hozircha ma'lumot yo'q.\n"
            "Quiz o'ynang va reytingga kiring!"
        )
    else:
        medals = ["🥇", "🥈", "🥉"]
        lines = ["🏆 <b>Reyting</b>\n"]
        for i, e in enumerate(entries[:10]):
            medal = medals[i] if i < 3 else f"{i + 1}."
            user_id = e.get("user_id", "")
            score = e.get("total_score", e.get("score", 0))
            lines.append(f"{medal} {user_id} — {score} ball")
        text = "\n".join(lines)

    tab_label = {"today": "Bugun", "week": "Hafta", "month": "Oy", "all": "Barchasi"}.get(period, "Barchasi")

    try:
        if edit:
            await message.edit_text(text, reply_markup=leaderboard_tabs_keyboard(period))
        else:
            await message.answer(text, reply_markup=leaderboard_tabs_keyboard(period))
    except Exception:
        await message.answer(text, reply_markup=leaderboard_tabs_keyboard(period))


# ─────────────────────────── Referal ───────────────────────────

@router.message(Command("invite"))
@router.message(F.text.in_({"👥 Taklif qilish", "👥 Invite"}))
async def show_referral(message: Message) -> None:
    user_id = message.from_user.id
    bot_info = await message.bot.get_me()
    bot_username = bot_info.username

    text = (
        f"👥 <b>Do'stlaringizni taklif qiling!</b>\n\n"
        f"Sizning link:\n"
        f"t.me/{bot_username}?start=ref_{user_id}\n\n"
        f"Har bir taklif uchun:\n"
        f"├── Siz: +50 XP + 3 kun premium\n"
        f"└── Do'st: +20 XP bonus"
    )

    await message.answer(text, reply_markup=referral_keyboard(bot_username, user_id))


@router.callback_query(F.data == "ref:copy")
async def copy_referral_link(cb: CallbackQuery) -> None:
    bot_info = await cb.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{cb.from_user.id}"
    await cb.answer(f"Link: {link}", show_alert=True)


@router.callback_query(F.data == "ref:invite")
async def referral_via_callback(cb: CallbackQuery) -> None:
    bot_info = await cb.bot.get_me()
    user_id = cb.from_user.id
    await cb.message.edit_text(
        f"👥 <b>Do'stlaringizni taklif qiling!</b>\n\n"
        f"Har bir taklif uchun: +50 XP + 3 kun premium",
        reply_markup=referral_keyboard(bot_info.username, user_id),
    )
    await cb.answer()
