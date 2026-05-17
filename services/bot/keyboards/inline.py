"""
All inline keyboards for the quiz bot.

Convention: every function returns an InlineKeyboardMarkup.
Callback data prefixes:
  qb:   quiz browse
  qp:   quiz play
  qg:   quiz group
  lb:   leaderboard
  pay:  payment
  prof: profile
  ref:  referral
  tg:   telegram group
  up:   upload / review
"""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def _kb(*rows: list[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=list(rows))


# ──────────────────────────── Quiz Browse ────────────────────────────


def quiz_browse_keyboard() -> InlineKeyboardMarkup:
    return _kb(
        [InlineKeyboardButton(text="📂 Mening quizlarim", callback_data="qb:my")],
        [InlineKeyboardButton(text="📌 Obunalarim", callback_data="qb:subs")],
        [InlineKeyboardButton(text="🌐 Ommaviy quizlar", callback_data="qb:public")],
        [InlineKeyboardButton(text="🔥 Trend", callback_data="qb:trending")],
        [InlineKeyboardButton(text="🎲 Tasodifiy", callback_data="qb:random")],
    )


def quiz_list_keyboard(
    quizzes: list[dict],
    page: int = 1,
    has_next: bool = False,
) -> InlineKeyboardMarkup:
    """Render a list of quiz items as buttons (max 5 per page)."""
    rows: list[list[InlineKeyboardButton]] = []
    for q in quizzes:
        label = f"📋 {q.get('name', 'Quiz')} ({q.get('total_questions', '?')} savol)"
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"qb:quiz:{q['id']}")]
        )

    nav: list[InlineKeyboardButton] = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="← Oldingi", callback_data=f"qb:page:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="Keyingi →", callback_data=f"qb:page:{page + 1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text="🏠 Menyu", callback_data="qb:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def set_select_keyboard(sets: list[dict], quiz_id: str) -> InlineKeyboardMarkup:
    """Show available sets for a quiz."""
    rows: list[list[InlineKeyboardButton]] = []
    for s in sets:
        num = s.get("set_number", 1)
        q_count = s.get("question_count", 20)
        pct = s.get("best_score_pct")
        status = f" ✅ {pct}%" if pct is not None else ""
        label = f"Set {num} ({q_count} savol){status}"
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"qp:set:{quiz_id}:{num}")]
        )
    rows.append([InlineKeyboardButton(text="◀ Orqaga", callback_data="qb:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ──────────────────────────── Time Selection ────────────────────────────


def time_select_keyboard(quiz_id: str, set_number: int) -> InlineKeyboardMarkup:
    return _kb(
        [
            InlineKeyboardButton(text="15s", callback_data=f"qp:time:{quiz_id}:{set_number}:15"),
            InlineKeyboardButton(text="30s", callback_data=f"qp:time:{quiz_id}:{set_number}:30"),
            InlineKeyboardButton(text="45s", callback_data=f"qp:time:{quiz_id}:{set_number}:45"),
            InlineKeyboardButton(text="60s", callback_data=f"qp:time:{quiz_id}:{set_number}:60"),
        ],
        [InlineKeyboardButton(text="◀ Orqaga", callback_data=f"qp:back_set:{quiz_id}")],
    )


def quiz_start_keyboard(quiz_id: str, set_number: int, time_sec: int) -> InlineKeyboardMarkup:
    return _kb(
        [
            InlineKeyboardButton(
                text="▶️ Boshlash",
                callback_data=f"qp:start:{quiz_id}:{set_number}:{time_sec}",
            ),
            InlineKeyboardButton(
                text="⏱ Vaqtni o'zgartirish",
                callback_data=f"qp:change_time:{quiz_id}:{set_number}",
            ),
        ],
        [InlineKeyboardButton(text="🏠 Menyu", callback_data="qb:menu")],
    )


# ──────────────────────────── In-Quiz Controls ────────────────────────────


def stop_quiz_keyboard(current: int, total: int) -> InlineKeyboardMarkup:
    return _kb(
        [
            InlineKeyboardButton(
                text="⏹ To'xtatish va natija ko'rish", callback_data="qp:stop_result"
            )
        ],
        [
            InlineKeyboardButton(
                text="💾 Saqlash (keyinroq davom)", callback_data="qp:stop_save"
            )
        ],
        [InlineKeyboardButton(text="▶️ Davom etish", callback_data="qp:continue")],
    )


def pause_quiz_keyboard() -> InlineKeyboardMarkup:
    return _kb(
        [InlineKeyboardButton(text="▶️ Davom etish", callback_data="qp:continue")],
        [InlineKeyboardButton(text="💾 Saqlash va chiqish", callback_data="qp:pause_save")],
    )


def saved_quiz_keyboard(quiz_id: str, set_number: int, time_sec: int) -> InlineKeyboardMarkup:
    return _kb(
        [
            InlineKeyboardButton(
                text="▶️ Davom (to'xtagan joydan)",
                callback_data=f"qp:resume:{quiz_id}:{set_number}:{time_sec}",
            ),
            InlineKeyboardButton(
                text="🔄 Boshidan",
                callback_data=f"qp:restart:{quiz_id}:{set_number}:{time_sec}",
            ),
        ],
    )


# ──────────────────────────── Quiz Results ────────────────────────────


def quiz_result_keyboard(
    quiz_id: str,
    set_number: int,
    next_set: int | None,
    has_wrong: bool,
    time_sec: int = 30,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if next_set is not None:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🔄 Set {next_set} ga o'tish",
                    callback_data=f"qp:set:{quiz_id}:{next_set}",
                )
            ]
        )

    if has_wrong:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🔁 Xatolarni qayta ishlash",
                    callback_data=f"qp:retry:{quiz_id}:{set_number}",
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text="📊 Xatolarni ko'rish",
                    callback_data=f"qp:show_wrong:{quiz_id}:{set_number}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="📤 Natija ulashish",
                callback_data=f"qp:share_result:{quiz_id}:{set_number}",
            )
        ]
    )
    rows.append([InlineKeyboardButton(text="🏠 Menyu", callback_data="qb:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def retry_result_keyboard(quiz_id: str, set_number: int, still_wrong: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if still_wrong > 0:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🔁 Yana {still_wrong} ta qoldi",
                    callback_data=f"qp:retry:{quiz_id}:{set_number}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="🏠 Menyu", callback_data="qb:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ──────────────────────────── Upload / Review ────────────────────────────


def upload_menu_keyboard() -> InlineKeyboardMarkup:
    return _kb(
        [InlineKeyboardButton(text="📄 Fayl yuklash", callback_data="up:file")],
        [InlineKeyboardButton(text="📷 Rasm yuborish", callback_data="up:image")],
        [InlineKeyboardButton(text="✍️ Qo'lda yozish", callback_data="up:manual")],
        [InlineKeyboardButton(text="🏠 Menyu", callback_data="qb:menu")],
    )


def image_upload_keyboard() -> InlineKeyboardMarkup:
    return _kb(
        [InlineKeyboardButton(text="✅ Tamom", callback_data="up:image_done")],
        [InlineKeyboardButton(text="❌ Bekor", callback_data="up:cancel")],
    )


def review_keyboard(task_id: str) -> InlineKeyboardMarkup:
    return _kb(
        [InlineKeyboardButton(text="✅ Saqlash", callback_data=f"up:save:{task_id}")],
        [InlineKeyboardButton(text="👁 Ko'rib chiqish", callback_data=f"up:preview:{task_id}")],
        [InlineKeyboardButton(text="⏭ Xatolarni o'tkazib yuborish", callback_data=f"up:skip_errors:{task_id}")],
        [InlineKeyboardButton(text="✏️ Qo'lda tuzatish", callback_data=f"up:manual_fix:{task_id}")],
        [InlineKeyboardButton(text="❌ Bekor", callback_data="up:cancel")],
    )


def visibility_keyboard(task_id: str) -> InlineKeyboardMarkup:
    return _kb(
        [
            InlineKeyboardButton(text="🔒 Faqat men", callback_data=f"up:vis:{task_id}:private"),
            InlineKeyboardButton(text="🌐 Ommaviy", callback_data=f"up:vis:{task_id}:public"),
        ],
    )


# ──────────────────────────── Quiz Group ────────────────────────────


def quiz_group_keyboard(group_id: int) -> InlineKeyboardMarkup:
    return _kb(
        [InlineKeyboardButton(text="📂 Quiz biriktirish", callback_data=f"qg:attach:{group_id}")],
        [InlineKeyboardButton(text="📢 Xabar yuborish", callback_data=f"qg:broadcast:{group_id}")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data=f"qg:stats:{group_id}")],
        [InlineKeyboardButton(text="📤 Link ulashish", callback_data=f"qg:share:{group_id}")],
        [InlineKeyboardButton(text="◀ Orqaga", callback_data="qg:list")],
    )


def quiz_group_list_keyboard(groups: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for g in groups:
        label = f"📌 {g['name']} ({g.get('subscriber_count', 0)} obunachi)"
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"qg:view:{g['id']}")]
        )
    rows.append(
        [InlineKeyboardButton(text="➕ Yangi guruh", callback_data="qg:create")]
    )
    rows.append([InlineKeyboardButton(text="🏠 Menyu", callback_data="qb:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def subscribe_group_keyboard(group_id: int, is_subscribed: bool) -> InlineKeyboardMarkup:
    if is_subscribed:
        sub_btn = InlineKeyboardButton(
            text="🔕 Obunadan chiqish", callback_data=f"qg:unsub:{group_id}"
        )
    else:
        sub_btn = InlineKeyboardButton(
            text="📌 Obuna bo'lish", callback_data=f"qg:sub:{group_id}"
        )
    return _kb(
        [sub_btn],
        [InlineKeyboardButton(text="▶️ O'ynash", callback_data=f"qg:play:{group_id}")],
        [InlineKeyboardButton(text="◀ Orqaga", callback_data="qb:subs")],
    )


# ──────────────────────────── Leaderboard ────────────────────────────


def leaderboard_tabs_keyboard(active_tab: str = "all", tag: str | None = None) -> InlineKeyboardMarkup:
    tabs = [
        ("Bugun", "today"),
        ("Hafta", "week"),
        ("Oy", "month"),
        ("Barchasi", "all"),
    ]
    nav: list[InlineKeyboardButton] = []
    for label, tab_id in tabs:
        if tab_id == active_tab:
            nav.append(
                InlineKeyboardButton(text=f"[{label}]", callback_data=f"lb:tab:{tab_id}")
            )
        else:
            nav.append(
                InlineKeyboardButton(text=label, callback_data=f"lb:tab:{tab_id}")
            )

    tag_suffix = f":{tag}" if tag else ""
    rows: list[list[InlineKeyboardButton]] = [
        nav,
        [
            InlineKeyboardButton(
                text="🏷 Teg bo'yicha filter",
                callback_data=f"lb:tag_filter{tag_suffix}",
            )
        ],
        [InlineKeyboardButton(text="🏠 Menyu", callback_data="qb:menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ──────────────────────────── Payment ────────────────────────────


def payment_keyboard() -> InlineKeyboardMarkup:
    return _kb(
        [InlineKeyboardButton(text="⭐ Telegram Stars bilan to'lash", callback_data="pay:stars")],
        [InlineKeyboardButton(text="👥 Do'st taklif qilib yutish", callback_data="ref:invite")],
        [InlineKeyboardButton(text="❌ Yopish", callback_data="pay:close")],
    )


def premium_plans_keyboard() -> InlineKeyboardMarkup:
    return _kb(
        [InlineKeyboardButton(text="📅 Oylik — 29 000 so'm", callback_data="pay:monthly")],
        [InlineKeyboardButton(text="📆 Yillik — 249 000 so'm (29% tejash)", callback_data="pay:yearly")],
        [InlineKeyboardButton(text="👥 Taklif qilib yutish", callback_data="ref:invite")],
        [InlineKeyboardButton(text="◀ Orqaga", callback_data="prof:view")],
    )


# ──────────────────────────── Profile ────────────────────────────


def profile_keyboard() -> InlineKeyboardMarkup:
    return _kb(
        [
            InlineKeyboardButton(text="📊 Batafsil", callback_data="prof:detail"),
            InlineKeyboardButton(text="💎 Obuna", callback_data="prof:premium"),
        ],
        [InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="prof:settings")],
        [InlineKeyboardButton(text="📌 Quiz Guruhlarim", callback_data="qg:list")],
    )


# ──────────────────────────── Referral ────────────────────────────


def referral_keyboard(bot_username: str, user_id: int) -> InlineKeyboardMarkup:
    link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    return _kb(
        [
            InlineKeyboardButton(text="📤 Ulashish", switch_inline_query=link),
        ],
        [InlineKeyboardButton(text="📋 Link nusxalash", callback_data="ref:copy")],
        [InlineKeyboardButton(text="🏠 Menyu", callback_data="qb:menu")],
    )


# ──────────────────────────── Telegram Group ────────────────────────────


def tg_group_settings_keyboard(voting: bool, who: str) -> InlineKeyboardMarkup:
    voting_label = "✅ Yoqilgan" if voting else "❌ O'chirilgan"
    admin_label = "●" if who == "admin" else " "
    all_label = "●" if who == "all" else " "
    return _kb(
        [
            InlineKeyboardButton(
                text=f"Voting: {voting_label}",
                callback_data="tg:toggle_voting",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"({admin_label}) Faqat admin",
                callback_data="tg:who:admin",
            ),
            InlineKeyboardButton(
                text=f"({all_label}) Hammasi",
                callback_data="tg:who:all",
            ),
        ],
        [InlineKeyboardButton(text="💾 Saqlash", callback_data="tg:save_settings")],
    )


def voting_keyboard(msg_id: int, voter_count: int) -> InlineKeyboardMarkup:
    return _kb(
        [
            InlineKeyboardButton(
                text=f"✅ Men ham tayyorman! ({voter_count})",
                callback_data=f"tg:vote:{msg_id}",
            )
        ],
        [InlineKeyboardButton(text="🚀 Hozir boshlash (admin)", callback_data=f"tg:force_start:{msg_id}")],
    )


def group_result_keyboard() -> InlineKeyboardMarkup:
    return _kb(
        [InlineKeyboardButton(text="🔄 Yana o'ynash", callback_data="tg:replay")],
        [InlineKeyboardButton(text="📊 Batafsil", callback_data="tg:detail")],
    )
