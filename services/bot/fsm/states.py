"""
Full State Machine for Quiz Bot (aiogram FSM).

States match BOT_UX.md §19:
  IDLE, QUIZ_SETUP, QUIZ_PLAYING, PAUSED, STOPPED,
  FILE_UPLOAD, PROCESSING, REVIEW, MANUAL_CREATE
"""
from aiogram.fsm.state import State, StatesGroup


class QuizStates(StatesGroup):
    # ── Main flow ──────────────────────────────────────────────────────────
    IDLE = State()
    """Default state — main menu is visible, any button can be pressed."""

    # ── Quiz browse / setup ───────────────────────────────────────────────
    QUIZ_SETUP = State()
    """User is selecting collection → set → time before starting a quiz."""

    BROWSING_MY_QUIZZES = State()
    """User is viewing their own collections list."""

    BROWSING_PUBLIC = State()
    """User is browsing public / trending quizzes or performing a search."""

    BROWSING_SUBSCRIPTIONS = State()
    """User is viewing subscribed quiz groups."""

    # ── Active quiz ───────────────────────────────────────────────────────
    QUIZ_PLAYING = State()
    """Polls are being sent one by one. PollAnswer updates are handled."""

    PAUSED = State()
    """Auto-pause after 2 consecutive skips. Awaiting resume or save."""

    STOPPED = State()
    """User manually stopped (/stop). Awaiting choice: results/save/continue."""

    # ── Upload flow ───────────────────────────────────────────────────────
    FILE_UPLOAD = State()
    """Awaiting a file (.docx/.pdf/.xlsx/.txt) from the user."""

    IMAGE_UPLOAD = State()
    """Awaiting one or more images from the user (multi-image, then Tamom)."""

    PROCESSING = State()
    """AI engine is processing the file/images. User is waiting."""

    REVIEW = State()
    """AI processing done. User reviews the result and confirms or edits."""

    # ── Manual quiz creation ──────────────────────────────────────────────
    MANUAL_CREATE = State()
    """Step-by-step: quiz name → savol → variantlar → javob → yana savol?"""

    MANUAL_CREATE_QUESTION = State()
    """Waiting for the question text in manual creation flow."""

    MANUAL_CREATE_OPTIONS = State()
    """Waiting for answer options (one per message, up to 10)."""

    MANUAL_CREATE_CORRECT = State()
    """Waiting for user to pick the correct answer index."""

    # ── Quiz Group management ─────────────────────────────────────────────
    QUIZ_GROUP_CREATE_NAME = State()
    """Awaiting quiz group name."""

    QUIZ_GROUP_CREATE_DESC = State()
    """Awaiting quiz group description."""

    QUIZ_GROUP_CREATE_TAGS = State()
    """Awaiting quiz group tags."""

    QUIZ_GROUP_BROADCAST = State()
    """Awaiting broadcast message text to send to subscribers."""

    # ── Telegram group (in-chat) settings ────────────────────────────────
    TG_GROUP_SETTINGS = State()
    """Admin is changing Telegram group quiz settings."""

    TG_GROUP_VOTING = State()
    """Voting is active in a Telegram group: waiting for voters."""

    TG_GROUP_PLAYING = State()
    """Telegram group quiz is in progress."""

    # ── Search ────────────────────────────────────────────────────────────
    SEARCHING = State()
    """User typed search query or selected a tag."""
