"""Profil, reyting va referal handlerlari."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup,
    LabeledPrice, PreCheckoutQuery,
)

from keyboards.inline import (
    profile_keyboard, leaderboard_tabs_keyboard,
    referral_keyboard, premium_plans_keyboard, payment_keyboard,
)
from utils.api import game_client, subscription_client
from utils.i18n import t

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
    lang = "uz"
    if isinstance(event, CallbackQuery):
        # Try to get lang from DB or default
        try:
            from db import AsyncSessionLocal
            from db.models import User
            from sqlalchemy import select
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(User).where(User.telegram_id == event.from_user.id)
                )
                user = result.scalar_one_or_none()
                if user:
                    lang = user.language_code or "uz"
        except Exception:
            pass

    text = t("premium_description", lang)

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=premium_plans_keyboard())
        await event.answer()
    else:
        await event.answer(text, reply_markup=premium_plans_keyboard())


@router.callback_query(F.data.in_({"pay:monthly", "pay:yearly"}))
async def show_payment_options(cb: CallbackQuery) -> None:
    period = "monthly" if cb.data == "pay:monthly" else "yearly"
    # Get user language
    lang = "uz"
    try:
        from db import AsyncSessionLocal
        from db.models import User
        from sqlalchemy import select
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == cb.from_user.id)
            )
            user = result.scalar_one_or_none()
            if user:
                lang = user.language_code or "uz"
    except Exception:
        pass
    period_labels = {
        "monthly": {"uz": "Oylik", "ru": "Ежемесячный", "en": "Monthly"},
        "yearly": {"uz": "Yillik", "ru": "Годовой", "en": "Yearly"},
    }
    price_labels = {
        "monthly": {"uz": "29 000 so'm", "ru": "29 000 сум", "en": "29 000 UZS"},
        "yearly": {"uz": "249 000 so'm", "ru": "249 000 сум", "en": "249 000 UZS"},
    }
    period_label = period_labels.get(period, {}).get(lang, period)
    price_label = price_labels.get(period, {}).get(lang, "")
    await cb.message.edit_text(
        t("payment_select", lang, period=period_label, price=price_label),
        reply_markup=payment_keyboard(period),
    )
    await cb.answer()


# Telegram Stars narxlari (1 USD ≈ 50 Stars)
_STARS_PRICES = {
    "monthly": 150,   # ~3 USD
    "yearly": 1200,   # ~24 USD
}
_PLAN_DAYS = {
    "monthly": 30,
    "yearly": 365,
}


@router.callback_query(F.data.startswith("pay:stars:"))
async def pay_with_stars(cb: CallbackQuery) -> None:
    """Telegram Stars orqali to'lov invoice yuborish."""
    period = cb.data.split(":")[2]  # "monthly" yoki "yearly"
    stars = _STARS_PRICES.get(period, 150)
    period_uz = "Oylik" if period == "monthly" else "Yillik"

    await cb.message.answer_invoice(
        title=f"💎 Premium — {period_uz}",
        description=(
            f"Quiz Bot Premium obuna ({period_uz})\n"
            "✅ Cheksiz fayl yuklash\n"
            "✅ Guruhga ulashish\n"
            "✅ Batafsil statistika"
        ),
        payload=f"premium:{period}:{cb.from_user.id}",
        currency="XTR",
        prices=[LabeledPrice(label=f"Premium {period_uz}", amount=stars)],
    )
    await cb.answer()


@router.pre_checkout_query()
async def process_pre_checkout(query: PreCheckoutQuery) -> None:
    """Telegram Stars to'lovdan oldin tasdiqlash."""
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def payment_successful(message: Message) -> None:
    """Muvaffaqiyatli to'lovdan keyin premium yoqish."""
    payload = message.successful_payment.invoice_payload
    # payload format: "premium:monthly:telegram_id" yoki "premium:yearly:telegram_id"
    parts = payload.split(":")
    if len(parts) >= 2:
        period = parts[1]
        days = _PLAN_DAYS.get(period, 30)

        try:
            from utils.api import subscription_client
            await subscription_client().activate_premium(
                user_id=message.from_user.id,
                days=days,
                source="stars",
            )
        except Exception:
            pass

    # Try to get user language
    lang = "uz"
    try:
        from db import AsyncSessionLocal
        from db.models import User as _User
        from sqlalchemy import select as _select
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                _select(_User).where(_User.telegram_id == message.from_user.id)
            )
            u = result.scalar_one_or_none()
            if u:
                lang = u.language_code or "uz"
    except Exception:
        pass

    period_labels = {"monthly": {"uz": "oylik", "ru": "ежемесячный", "en": "monthly"},
                     "yearly": {"uz": "yillik", "ru": "годовой", "en": "yearly"}}
    period_label = period_labels.get(period, {}).get(lang, period)
    await message.answer(t("payment_success", lang, period=period_label))


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

    # Get user language
    lang = "uz"
    try:
        if hasattr(message, "from_user") and message.from_user:
            from db import AsyncSessionLocal
            from db.models import User
            from sqlalchemy import select
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(User).where(User.telegram_id == message.from_user.id)
                )
                user = result.scalar_one_or_none()
                if user:
                    lang = user.language_code or "uz"
    except Exception:
        pass

    try:
        data = await game_client().get_leaderboard(period=api_period, limit=10)
        entries = data.get("entries", [])
    except Exception:
        entries = []

    if not entries:
        text = t("leaderboard_title", lang) + "\n\n" + t("leaderboard_empty", lang)
    else:
        medals = ["🥇", "🥈", "🥉"]
        lines = [t("leaderboard_title", lang) + "\n"]
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
@router.message(F.text.in_({"👥 Taklif qilish", "👥 Пригласить", "👥 Invite"}))
async def show_referral(message: Message) -> None:
    user_id = message.from_user.id
    bot_info = await message.bot.get_me()
    bot_username = bot_info.username

    # Get user language
    lang = "uz"
    try:
        from db import AsyncSessionLocal
        from db.models import User
        from sqlalchemy import select
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.telegram_id == user_id))
            user = result.scalar_one_or_none()
            if user:
                lang = user.language_code or "uz"
    except Exception:
        pass

    text = (
        t("referral_description", lang)
        + f"\n<code>https://t.me/{bot_username}?start=ref_{user_id}</code>"
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

    lang = "uz"
    try:
        from db import AsyncSessionLocal
        from db.models import User
        from sqlalchemy import select
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.telegram_id == user_id))
            user = result.scalar_one_or_none()
            if user:
                lang = user.language_code or "uz"
    except Exception:
        pass

    text = (
        t("referral_description", lang)
        + f"\n<code>https://t.me/{bot_info.username}?start=ref_{user_id}</code>"
    )
    await cb.message.edit_text(text, reply_markup=referral_keyboard(bot_info.username, user_id))
    await cb.answer()
