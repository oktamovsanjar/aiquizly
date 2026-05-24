"""Profil, reyting va referal handlerlari."""

import asyncio
import logging

from aiogram import Router, F

logger = logging.getLogger(__name__)
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    PreCheckoutQuery,
)

from keyboards.inline import (
    profile_keyboard,
    leaderboard_tabs_keyboard,
    referral_keyboard,
    premium_plans_keyboard,
    payment_keyboard,
    back_to_profile_keyboard,
)
from utils.api import game_client, subscription_client
from utils.i18n import t

router = Router()

# Yangi 11-tier tizimi (Faza 2)
LEVEL_TIER_ICONS = {
    "beginner": "🌱",
    "student": "📗",
    "expert": "📘",
    "skilled": "📙",
    "experienced": "📕",
    "mentor": "🎓",
    "sage": "🦉",
    "professor": "🏛",
    "academic": "👑",
    "legendary": "⭐",
    "legend": "🏆",
}

LEVEL_TIER_NAMES_UZ = {
    "beginner": "Yangi boshlovchi",
    "student": "Talaba",
    "expert": "Bilimdon",
    "skilled": "Mahoratli",
    "experienced": "Tajribali",
    "mentor": "Ustoz",
    "sage": "Donishmand",
    "professor": "Professor",
    "academic": "Akademik",
    "legendary": "Afsonaviy",
    "legend": "Legenda",
}

# Eski 6-tier tizimi — backward compat (eski cache larda hali bo'lishi mumkin)
LEGACY_LEVEL_MAP = {
    "learner": "student",   # eski 'learner' -> yangi 'student'
    "master": "skilled",    # eski 'master' -> yangi 'skilled'
}

# Birlashtirilgan map'lar — eski va yangi keylar ham ishlashi uchun
LEVEL_ICONS = {**LEVEL_TIER_ICONS}
LEVEL_NAMES_UZ = {**LEVEL_TIER_NAMES_UZ}
# Eski keylar uchun mappings
for old, new in LEGACY_LEVEL_MAP.items():
    LEVEL_ICONS[old] = LEVEL_TIER_ICONS[new]
    LEVEL_NAMES_UZ[old] = LEVEL_TIER_NAMES_UZ[new]


# Level progress helper'i — server bilan bir xil formula (50 * N^1.7)
def _xp_for_level(level: int) -> int:
    if level <= 1:
        return 0
    if level > 100:
        level = 100
    return round(50.0 * (level ** 1.7))


def compute_level_progress(total_xp: int) -> tuple[int, int, int, float]:
    """Joriy daraja ichidagi progress. Server LevelProgress bilan mos.

    Returns: (level, current_xp, needed_xp, ratio)
    """
    if total_xp < 0:
        total_xp = 0
    # Binary search
    lo, hi = 1, 100
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _xp_for_level(mid) <= total_xp:
            lo = mid
        else:
            hi = mid - 1
    level = lo
    if level >= 100:
        return 100, 0, 0, 1.0
    base = _xp_for_level(level)
    next_xp = _xp_for_level(level + 1)
    cur = total_xp - base
    needed = next_xp - base
    ratio = cur / needed if needed > 0 else 1.0
    return level, cur, needed, max(0.0, min(1.0, ratio))


def _progress_bar(ratio: float, width: int = 12) -> str:
    filled = int(round(ratio * width))
    return "█" * filled + "░" * (width - filled)


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

    # Game + Subscription parallel so'rovlar
    stats_result, sub_result = await asyncio.gather(
        game_client().get_user_stats(user.id),
        subscription_client().get_plan(user.id),
        return_exceptions=True,
    )
    stats = stats_result if isinstance(stats_result, dict) else {}
    sub = sub_result if isinstance(sub_result, dict) else {}
    plan = sub.get("plan", "free")
    expires_at = sub.get("expires_at")

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

    # Daraja progress
    level_num, cur_xp, needed_xp, ratio = compute_level_progress(total_xp)
    bar = _progress_bar(ratio, width=12)
    remaining_xp = max(0, needed_xp - cur_xp)

    # Yutuqlar soni (alohida endpoint kerak emas — keyingi quizdan keyin yangilanadi)
    ach_count = stats.get("achievements_count")

    plan_text = (
        "💎 Premium"
        if plan == "premium"
        else ("🏢 Business" if plan == "business" else "🆓 Free")
    )
    if expires_at:
        plan_text += f" (→ {expires_at[:10]})"

    text = (
        f"👤 <b>{user.full_name}</b>\n"
        f"{level_icon} <b>{level_name}</b> · Lvl {level_num}\n"
        f"⚡ <b>{total_xp:,}</b> XP   ·   🔥 {streak} kun\n"
        f"[{bar}] {int(ratio*100)}%\n"
    )
    if level_num < 100:
        text += f"Lvl {level_num+1} gacha: <b>{remaining_xp} XP</b>\n"
    else:
        text += "🏆 Eng yuqori darajaga yetdingiz!\n"

    text += (
        f"\n📊 <b>Statistika</b>\n"
        f"├── 🎮 O'ynagan: <b>{total_games}</b> quiz\n"
        f"├── ✅ To'g'ri: <b>{total_correct:,}</b>\n"
        f"├── ❌ Noto'g'ri: <b>{total_wrong:,}</b>\n"
        f"├── 🎯 Aniqlik: <b>{accuracy:.0f}%</b>\n"
        f"└── 📚 Jami savollar: <b>{total_q:,}</b>\n"
    )
    if ach_count is not None:
        text += f"🏅 Yutuqlar: <b>{ach_count}/24</b>\n"

    text += f"\n{plan_text}"

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
    total_xp = stats.get("total_xp", 0)
    level_num, cur_xp, needed_xp, ratio = compute_level_progress(total_xp)
    bar = _progress_bar(ratio, width=14)
    text = (
        f"📊 <b>Batafsil statistika</b>\n\n"
        f"🎮 Jami o'yinlar: {stats.get('total_games', 0):,}\n"
        f"✅ To'g'ri: {stats.get('total_correct', 0):,}\n"
        f"❌ Noto'g'ri: {stats.get('total_wrong', 0):,}\n"
        f"🎯 Aniqlik: {stats.get('accuracy', 0):.1f}%\n\n"
        f"⭐ Jami XP: <b>{total_xp:,}</b>\n"
        f"🏆 Daraja: {LEVEL_ICONS.get(level, '🌱')} {LEVEL_NAMES_UZ.get(level, 'Yangi')} · Lvl {level_num}\n"
        f"[{bar}] {int(ratio*100)}%\n"
    )
    if level_num < 100:
        text += f"Lvl {level_num+1} gacha: <b>{max(0, needed_xp - cur_xp)} XP</b>\n"
    text += (
        f"\n🔥 Hozirgi streak: {stats.get('current_streak', 0)} kun\n"
        f"📈 Eng uzun streak: {stats.get('longest_streak', 0)} kun"
    )

    await cb.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="◀ Orqaga", callback_data="prof:view")]
            ]
        ),
    )
    await cb.answer()


# ─────────────────────────── Yutuqlar ───────────────────────────


@router.callback_query(F.data == "prof:achievements")
async def show_achievements(cb: CallbackQuery) -> None:
    """Yutuqlar sahifasi — ochilgan va yopiq yutuqlar ro'yxati."""
    try:
        data = await game_client().get_user_achievements(cb.from_user.id)
    except Exception as e:
        logger.warning("yutuqlar olishda xato: %s", e)
        data = {}

    unlocked = data.get("unlocked") or []
    locked = data.get("locked") or []
    total = data.get("total", len(unlocked) + len(locked))

    lines = [f"🏅 <b>Yutuqlar</b> ({len(unlocked)}/{total})\n"]

    if unlocked:
        lines.append("✅ <b>Ochilgan:</b>")
        # Eng oxirgi 15 ta ochilgan (UX uchun, 24+ bo'lsa ham)
        for ach in unlocked[:15]:
            icon = ach.get("icon") or "🏅"
            name = ach.get("name") or ach.get("slug", "")
            desc = ach.get("description") or ""
            xp = ach.get("xp_reward", 0)
            xp_suf = f" (+{xp} XP)" if xp > 0 else ""
            lines.append(f"{icon} <b>{name}</b> — {desc}{xp_suf}")
        if len(unlocked) > 15:
            lines.append(f"<i>...va yana {len(unlocked) - 15} ta</i>")
        lines.append("")

    if locked:
        lines.append("🔒 <b>Yopiq:</b>")
        # Faqat dastlabki 10 ta (jonli "yopiq" yutuqlar — motivatsiya)
        for ach in locked[:10]:
            name = ach.get("name") or ach.get("slug", "")
            desc = ach.get("description") or ""
            xp = ach.get("xp_reward", 0)
            xp_suf = f" (+{xp} XP)" if xp > 0 else ""
            lines.append(f"❓ <i>{name}</i> — {desc}{xp_suf}")
        if len(locked) > 10:
            lines.append(f"<i>...va yana {len(locked) - 10} ta yopiq</i>")

    if not unlocked and not locked:
        lines.append("<i>Hozircha yutuqlar yo'q. Birinchi quizni yeching!</i>")

    text = "\n".join(lines)

    try:
        await cb.message.edit_text(text, reply_markup=back_to_profile_keyboard())
    except Exception:
        await cb.message.answer(text, reply_markup=back_to_profile_keyboard())
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
        "monthly": {"uz": "1 ⭐ (aksiya!)", "ru": "1 ⭐ (акция!)", "en": "1 ⭐ (sale!)"},
        "yearly": {"uz": "1 ⭐ (aksiya!)", "ru": "1 ⭐ (акция!)", "en": "1 ⭐ (sale!)"},
    }
    period_label = period_labels.get(period, {}).get(lang, period)
    price_label = price_labels.get(period, {}).get(lang, "")
    await cb.message.edit_text(
        t("payment_select", lang, period=period_label, price=price_label),
        reply_markup=payment_keyboard(period),
    )
    await cb.answer()


# Aksiya narxi
_STARS_PRICES = {
    "monthly": 1,
    "yearly": 1,
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

    period_labels = {
        "monthly": {"uz": "oylik", "ru": "ежемесячный", "en": "monthly"},
        "yearly": {"uz": "yillik", "ru": "годовой", "en": "yearly"},
    }
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
    await _send_leaderboard(message, "all", caller_id=message.from_user.id)


@router.callback_query(F.data.startswith("lb:tab:"))
async def leaderboard_tab(cb: CallbackQuery) -> None:
    tab = cb.data.split(":")[2]
    await _send_leaderboard(cb.message, tab, edit=True, caller_id=cb.from_user.id)
    await cb.answer()


async def _send_leaderboard(
    message: Message, period: str, edit: bool = False, caller_id: int | None = None
) -> None:
    api_period = {
        "today": "daily",
        "week": "weekly",
        "month": "monthly",
        "all": "alltime",
    }.get(period, "alltime")
    period_label = {
        "today": "Bugun",
        "week": "Hafta",
        "month": "Oy",
        "all": "Barchasi",
    }.get(period, "Barchasi")

    user_tg_id = caller_id or (message.from_user.id if message.from_user else None)

    # Avval o'z rank ni topamiz — atrofini qancha katta tortishni belgilash uchun
    rank_data = None
    if user_tg_id:
        try:
            rank_data = await game_client().get_user_rank(user_tg_id, period=api_period)
        except Exception:
            rank_data = None

    my_rank = int(rank_data.get("rank", 0)) if rank_data else 0
    my_score = int(rank_data.get("total", 0)) if rank_data else 0

    # Agar foydalanuvchi 10 dan past bo'lsa, kattaroq slice olamiz (atrofini ko'rsatish uchun)
    fetch_limit = 10
    if my_rank > 10:
        fetch_limit = max(my_rank + 2, 50)

    entries = []
    try:
        lb_data = await game_client().get_leaderboard(period=api_period, limit=fetch_limit)
        entries = lb_data.get("entries") or []
    except Exception as e:
        logger.warning("leaderboard olishda xato: %s", e)

    # UUID → user ma'lumotlari (first_name, username, telegram_id)
    user_info: dict = {}
    if entries:
        from db import AsyncSessionLocal
        from sqlalchemy import text as _text
        uuid_list = [e.get("UserID") or e.get("user_id", "") for e in entries if e.get("UserID") or e.get("user_id")]
        if uuid_list:
            try:
                async with AsyncSessionLocal() as session:
                    rows = await session.execute(
                        _text("SELECT id::text, telegram_id, first_name, username FROM users WHERE id = ANY(:ids)"),
                        {"ids": uuid_list},
                    )
                    for row in rows.fetchall():
                        user_info[row[0]] = {"telegram_id": row[1], "first_name": row[2], "username": row[3]}
            except Exception:
                pass

    def _render_row(idx: int, e: dict) -> str:
        medals = ["🥇", "🥈", "🥉"]
        medal = medals[idx] if idx < 3 else f"  {idx + 1}."
        uid = e.get("UserID") or e.get("user_id", "")
        info = user_info.get(uid, {})
        name = (
            (info.get("username") and f"@{info['username']}")
            or info.get("first_name")
            or e.get("first_name")
            or "User"
        )
        tg_id = info.get("telegram_id")
        score = e.get("Score", e.get("total_score", e.get("score", 0)))
        marker = " 👈" if tg_id == user_tg_id else ""
        return f"{medal} <b>{name}</b> — {int(score):,} XP{marker}"

    if not entries:
        text = f"🏆 <b>Reyting — {period_label}</b>\n\n<i>Hozircha ma'lumot yo'q</i>"
    else:
        lines = [f"🏆 <b>Reyting — {period_label}</b>\n"]
        top10 = entries[:10]
        for i, e in enumerate(top10):
            lines.append(_render_row(i, e))

        # Agar foydalanuvchi top-10 dan tashqarida bo'lsa, atrofini ko'rsatamiz
        if my_rank > 10 and len(entries) > 10:
            # ±2 atrof: my_rank-2 .. my_rank+2
            target_lo = max(11, my_rank - 2)
            target_hi = my_rank + 2
            around = [
                (i, e) for i, e in enumerate(entries)
                if target_lo <= (i + 1) <= target_hi
            ]
            if around:
                lines.append("   ⋮")
                for idx, e in around:
                    lines.append(_render_row(idx, e))

            # Top-10 ga yetish uchun qancha XP kerakligi
            if len(top10) >= 10:
                top10_score = top10[9].get(
                    "Score", top10[9].get("total_score", top10[9].get("score", 0))
                )
                if my_score < int(top10_score):
                    gap = int(top10_score) - my_score + 1
                    lines.append(f"\n🎯 Top-10 ga kirish uchun: <b>{gap:,} XP</b> kerak")

        text = "\n".join(lines)

    # Foydalanuvchi top-10 da ham, atrofda ham yo'q bo'lsa (masalan, faqat rank API ishlatilgan)
    if my_rank > 0 and my_rank > (len(entries) if entries else 0):
        text += f"\n\n👤 <b>Sizning o'rningiz: {my_rank}-o'rin</b>"
        if my_score:
            text += f" — {my_score:,} XP"

    try:
        if edit:
            await message.edit_text(
                text, reply_markup=leaderboard_tabs_keyboard(period)
            )
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

    lang = "uz"
    referral_count = 0
    try:
        from db import AsyncSessionLocal
        from db.models import User, Referral
        from sqlalchemy import select, func

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                lang = user.language_code or "uz"
                count_result = await session.execute(
                    select(func.count()).select_from(Referral)
                    .where(Referral.referrer_id == user.id)
                )
                referral_count = count_result.scalar() or 0
    except Exception:
        pass

    invited_line = {
        "uz": f"👥 Taklif qilganlar: <b>{referral_count} kishi</b>\n\n",
        "ru": f"👥 Приглашённых: <b>{referral_count} чел.</b>\n\n",
        "en": f"👥 Invited: <b>{referral_count} people</b>\n\n",
    }.get(lang, "")

    text = (
        invited_line
        + t("referral_description", lang)
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
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                lang = user.language_code or "uz"
    except Exception:
        pass

    text = (
        t("referral_description", lang)
        + f"\n<code>https://t.me/{bot_info.username}?start=ref_{user_id}</code>"
    )
    await cb.message.edit_text(
        text, reply_markup=referral_keyboard(bot_info.username, user_id)
    )
    await cb.answer()


# ─────────────────────────── Sozlamalar ───────────────────────────

@router.callback_query(F.data == "prof:settings")
async def show_settings(cb: CallbackQuery) -> None:
    """Foydalanuvchi sozlamalari — til va quiz sozlamalari."""
    from utils.user_settings import get_user_settings
    from keyboards.language import language_keyboard
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    user_id = cb.from_user.id
    saved = await get_user_settings(user_id)

    time_sec = saved.get("time_sec", 30)
    shuffle_q = saved.get("shuffle_questions", True)
    shuffle_o = saved.get("shuffle_options", True)

    sq = "✅" if shuffle_q else "❌"
    so = "✅" if shuffle_o else "❌"

    text = (
        "⚙️ <b>Sozlamalar</b>\n\n"
        f"⏱ Savol vaqti: <b>{time_sec} soniya</b>\n"
        f"🔀 Savollar aralash: <b>{sq}</b>\n"
        f"🔀 Variantlar aralash: <b>{so}</b>\n\n"
        "<i>Vaqt va aralash sozlamalari quiz boshlanishida o'zgartiriladi.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="set:lang:uz"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set:lang:ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="set:lang:en"),
        ],
        [InlineKeyboardButton(text="◀ Orqaga", callback_data="prof:view")],
    ])
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("set:lang:"))
async def set_language(cb: CallbackQuery, state) -> None:
    """Tilni o'zgartirish."""
    from db import AsyncSessionLocal
    from db.models import User
    from sqlalchemy import update
    from keyboards.main_menu import main_menu_keyboard

    lang = cb.data.split(":")[2]
    lang_names = {"uz": "🇺🇿 O'zbek", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}

    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User)
            .where(User.telegram_id == cb.from_user.id)
            .values(language_code=lang)
        )
        await session.commit()

    await state.update_data(language_code=lang)
    await cb.answer(f"Til o'zgartirildi: {lang_names.get(lang, lang)}", show_alert=True)
    await show_settings(cb)
