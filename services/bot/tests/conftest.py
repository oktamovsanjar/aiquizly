"""
conftest.py — barcha bot testlari uchun aiogram va bot-specific
modullarni mock qiladi. Bu faylni pytest avtomatik yuklaydi.
"""

import sys
import types
from unittest.mock import MagicMock


def _mod(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m


# ── aiogram ────────────────────────────────────────────────────────────────────
_AIOGRAM_TYPES = [
    "Message",
    "CallbackQuery",
    "ReplyKeyboardMarkup",
    "KeyboardButton",
    "InlineKeyboardMarkup",
    "InlineKeyboardButton",
    "PollAnswer",
    "ChatMemberUpdated",
    "Poll",
    "PollOption",
    "Document",
    "PhotoSize",
    "ContentType",
    "BotCommand",
    "ChatMember",
    "Chat",
    "ReplyKeyboardRemove",
    "ForceReply",
    "Animation",
    "Audio",
    "Video",
    "Voice",
    "Sticker",
    "Location",
    "Contact",
    "Venue",
    "LabeledPrice",
    "PreCheckoutQuery",
    "SuccessfulPayment",
]


class _TransitionSentinel:
    """IS_MEMBER >> IS_NOT_MEMBER → MagicMock() (aiogram transition filter)."""

    def __rshift__(self, other):
        return MagicMock()

    def __lshift__(self, other):
        return MagicMock()

    def __rrshift__(self, other):
        return MagicMock()


_mod(
    "aiogram",
    Router=MagicMock,
    F=MagicMock(),
    Bot=MagicMock,
    IS_MEMBER=_TransitionSentinel(),
    IS_NOT_MEMBER=_TransitionSentinel(),
)


def _noop_filter(*a, **kw):
    return MagicMock()


_mod(
    "aiogram.filters",
    CommandStart=_noop_filter,
    Command=_noop_filter,
    StateFilter=_noop_filter,
    ChatMemberUpdatedFilter=_noop_filter,
    IS_MEMBER=_TransitionSentinel(),
    IS_NOT_MEMBER=_TransitionSentinel(),
)

_mod("aiogram.fsm")
_mod("aiogram.fsm.context", FSMContext=MagicMock)
_mod("aiogram.fsm.state", State=MagicMock, StatesGroup=MagicMock)

types_mod = _mod("aiogram.types", **{t: MagicMock for t in _AIOGRAM_TYPES})

_mod("aiogram.enums", ParseMode=MagicMock)
_mod("aiogram.client")
_mod("aiogram.client.default", DefaultBotProperties=MagicMock)
_mod("aiogram.webhook")
_mod(
    "aiogram.webhook.aiohttp_server",
    SimpleRequestHandler=MagicMock,
    setup_application=MagicMock,
)

# ── aiohttp ────────────────────────────────────────────────────────────────────
_mod("aiohttp")
_web = _mod("aiohttp.web")
for cls in ["Application", "AppRunner", "TCPSite", "Response", "Request"]:
    setattr(_web, cls, MagicMock)
setattr(_web, "run_app", MagicMock)
setattr(_web, "json_response", MagicMock)

# ── sqlalchemy ─────────────────────────────────────────────────────────────────
_mod(
    "sqlalchemy",
    select=MagicMock(return_value=MagicMock()),
    update=MagicMock(return_value=MagicMock()),
    insert=MagicMock(return_value=MagicMock()),
    delete=MagicMock(return_value=MagicMock()),
    func=MagicMock(),
    text=MagicMock(return_value=MagicMock()),
    BigInteger=MagicMock(),
    Boolean=MagicMock(),
    DateTime=MagicMock(),
    ForeignKey=MagicMock(),
    Index=MagicMock(),
    Integer=MagicMock(),
    String=MagicMock(),
    Text=MagicMock(),
    UniqueConstraint=MagicMock(),
)
_mod("sqlalchemy.ext")
_mod("sqlalchemy.ext.asyncio", AsyncSession=MagicMock, create_async_engine=MagicMock)
_mod(
    "sqlalchemy.orm",
    sessionmaker=MagicMock,
    DeclarativeBase=MagicMock,
    Mapped=MagicMock,
    mapped_column=MagicMock,
    relationship=MagicMock,
)
_mod("sqlalchemy.dialects")
_mod("sqlalchemy.dialects.postgresql", UUID=MagicMock, ARRAY=MagicMock)

# ── keyboards ──────────────────────────────────────────────────────────────────
_mod("keyboards")
_mod("keyboards.main_menu", main_menu_keyboard=MagicMock())
_mod("keyboards.language", language_keyboard=MagicMock())

_inline_fns = [
    "quiz_browse_keyboard",
    "quiz_list_keyboard",
    "my_quiz_list_keyboard",
    "quiz_manage_keyboard",
    "quiz_delete_confirm_keyboard",
    "set_select_keyboard",
    "time_select_keyboard",
    "quiz_start_keyboard",
    "stop_quiz_keyboard",
    "pause_quiz_keyboard",
    "saved_quiz_keyboard",
    "quiz_result_keyboard",
    "retry_result_keyboard",
    "upload_menu_keyboard",
    "image_upload_keyboard",
    "review_keyboard",
    "visibility_keyboard",
    "quiz_group_keyboard",
    "quiz_group_list_keyboard",
    "subscribe_group_keyboard",
    "leaderboard_tabs_keyboard",
    "payment_keyboard",
    "premium_plans_keyboard",
    "profile_keyboard",
    "referral_keyboard",
    "tg_group_settings_keyboard",
    "tg_group_linked_quizzes_keyboard",
    "tg_group_quiz_select_keyboard",
    "tg_group_quiz_start_keyboard",
    "voting_keyboard",
    "group_result_keyboard",
    # review flow
    "quiz_done_with_review_keyboard",
    "review_nav_keyboard",
    "review_answer_keyboard",
    "review_delete_confirm_keyboard",
]
_inline_mod = _mod("keyboards.inline", **{fn: MagicMock() for fn in _inline_fns})
_inline_mod.OPTION_LABELS = ["A", "B", "C", "D", "E", "F"]

# ── fsm ────────────────────────────────────────────────────────────────────────
_mod("fsm")
_mod("fsm.states", QuizStates=MagicMock())

# ── utils ──────────────────────────────────────────────────────────────────────
_mod("utils")
_mod(
    "utils.admin_notify",
    notify_admin=MagicMock(),
    notify_bot_started=MagicMock(),
    notify_new_user=MagicMock(),
)
_mod("utils.i18n", t=MagicMock(return_value=""))
_mod(
    "utils.api",
    ai_engine_client=MagicMock,
    subscription_client=MagicMock,
    game_client=MagicMock,
    notifier_client=MagicMock,
    GameClient=MagicMock,
    AIEngineClient=MagicMock,
    SubscriptionClient=MagicMock,
    NotifierClient=MagicMock,
    ServiceError=Exception,
)

# ── middlewares ────────────────────────────────────────────────────────────────
_mod("middlewares")
_mod("middlewares.subscription", SubscriptionMiddleware=MagicMock)


# ── db ─────────────────────────────────────────────────────────────────────────
# DB — model classlarini real attribute larli object sifatida yaratamiz
class _UserModel:
    telegram_id = MagicMock()
    id = MagicMock()
    referred_by = MagicMock()


class _ReferralModel(MagicMock):
    referrer_id = MagicMock()
    referred_id = MagicMock()


class _QuizGroupModel:
    owner_id = MagicMock()
    is_active = MagicMock()
    created_at = MagicMock()
    slug = MagicMock()
    id = MagicMock()


_mod("db", AsyncSessionLocal=MagicMock)
_mod(
    "db.models",
    User=_UserModel,
    QuizGroup=_QuizGroupModel,
    QuizGroupSubscriber=MagicMock,
    Referral=_ReferralModel,
    TelegramGroup=MagicMock,
)
_mod("db.queries")
