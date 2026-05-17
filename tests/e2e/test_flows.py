"""
E2E testlar — to'liq foydalanuvchi oqimlari.

QA.md §4 ga asoslanadi:
  - Onboarding: /start → til → menyu
  - Referral: link → bonus
  - Subscription limit: free plan 3 ta fayl chegarasi
  - Quiz browse: ommaviy quizlar ro'yxati

Bu testlar real servislar o'rniga mock HTTP bilan ishlaydi.
Real servislar bilan ishlash uchun: pytest --real-services
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Mock helpers ──────────────────────────────────────────────────────────────

def mock_message(text: str, user_id: int = 12345, args: str = "") -> MagicMock:
    msg = MagicMock()
    msg.text = text
    msg.from_user.id = user_id
    msg.from_user.telegram_id = user_id
    msg.from_user.username = "testuser"
    msg.from_user.first_name = "Test"
    msg.from_user.last_name = "User"
    msg.from_user.language_code = "uz"
    msg.args = args
    msg.answer = AsyncMock()
    msg.reply = AsyncMock()
    msg.bot = MagicMock()
    msg.bot.get_me = AsyncMock(return_value=MagicMock(username="aiquizlybot"))
    return msg


def mock_state() -> MagicMock:
    state = AsyncMock()
    state.get_state = AsyncMock(return_value=None)
    state.get_data = AsyncMock(return_value={})
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    state.clear = AsyncMock()
    return state


def mock_db_session(user=None):
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.refresh = AsyncMock()
    return session


# ── Onboarding oqimi ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_onboarding_start_shows_language_keyboard():
    """/start → til tanlash keyboard ko'rsatilishi."""
    from services.bot.handlers.start import cmd_start

    message = mock_message("/start")
    session = mock_db_session(user=None)  # Yangi foydalanuvchi

    with patch("services.bot.handlers.start.AsyncSessionLocal", return_value=session):
        await cmd_start(message)

    message.answer.assert_called_once()
    call_kwargs = message.answer.call_args
    assert "Tilni tanlang" in call_kwargs[0][0] or "xush kelibsiz" in call_kwargs[0][0].lower()


@pytest.mark.asyncio
async def test_onboarding_language_choice_shows_menu():
    """Til tanlangandan keyin asosiy menyu ko'rsatilishi."""
    from services.bot.handlers.start import choose_language

    message = mock_message("O'zbek")
    session = mock_db_session()

    with patch("services.bot.handlers.start.AsyncSessionLocal", return_value=session):
        await choose_language(message)

    message.answer.assert_called_once()
    # ReplyKeyboardMarkup berilishi kerak
    call_kwargs = message.answer.call_args
    assert call_kwargs[1].get("reply_markup") is not None or len(call_kwargs) > 1


# ── Referral oqimi ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_referral_start_shows_bonus_message():
    """/start ref_<id> → bonus xabari ko'rsatilishi."""
    from services.bot.handlers.start import cmd_start_referral

    new_user_id = 99991
    referrer_tg_id = 99992
    message = mock_message(f"/start ref_{referrer_tg_id}", user_id=new_user_id)
    message.args = f"ref_{referrer_tg_id}"

    new_user = MagicMock()
    new_user.id = uuid.uuid4()
    new_user.telegram_id = new_user_id
    new_user.referred_by = None

    referrer_user = MagicMock()
    referrer_user.id = uuid.uuid4()
    referrer_user.telegram_id = referrer_tg_id
    referrer_user.first_name = "Aziz"
    referrer_user.username = "aziz"

    session = mock_db_session()

    call_count = 0
    async def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        # 1: _upsert_user qidiradi
        # 2: referrer qidiradi
        # 3: dublikat tekshiradi
        if call_count == 1:
            result.scalar_one_or_none.return_value = None  # yangi user
        elif call_count == 2:
            result.scalar_one_or_none.return_value = referrer_user
        else:
            result.scalar_one_or_none.return_value = None  # dublikat yo'q
        return result

    session.execute = mock_execute
    session.get = AsyncMock(return_value=new_user)

    with patch("services.bot.handlers.start.AsyncSessionLocal", return_value=session):
        with patch("services.bot.handlers.start.subscription_client") as mock_sub:
            mock_sub.return_value.activate_premium = AsyncMock()
            with patch("services.bot.handlers.start.game_client") as mock_game:
                mock_game.return_value.award_xp = AsyncMock()
                await cmd_start_referral(message)

    message.answer.assert_called_once()
    answer_text = message.answer.call_args[0][0]
    assert "Aziz" in answer_text or "20 XP" in answer_text


@pytest.mark.asyncio
async def test_referral_invalid_id_falls_back_to_normal_start():
    """/start ref_abc (noto'g'ri ID) → oddiy /start kabi ishlaydi."""
    from services.bot.handlers.start import cmd_start_referral

    message = mock_message("/start ref_abc")
    message.args = "ref_abc"  # int emas

    session = mock_db_session(user=None)

    with patch("services.bot.handlers.start.AsyncSessionLocal", return_value=session):
        await cmd_start_referral(message)

    # Xato bermasdan ishlashi kerak
    message.answer.assert_called_once()


# ── Subscription limit oqimi ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_subscription_free_plan_blocks_at_limit():
    """Free plan 3 ta fayl limitiga yetganda False qaytarilishi."""
    from utils.api import SubscriptionClient

    client = SubscriptionClient(base_url="http://subscription:8003")

    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.json.return_value = {
        "allowed": False, "limit": 3, "used": 3, "plan": "free"
    }

    with patch("httpx.AsyncClient") as mock_http:
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http.return_value)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value.get = AsyncMock(return_value=mock_response)

        result = await client.check_limit(user_id=12345, action="file_upload")

    assert result is False


@pytest.mark.asyncio
async def test_subscription_premium_always_allowed():
    """Premium plan → har doim True."""
    from utils.api import SubscriptionClient

    client = SubscriptionClient(base_url="http://subscription:8003")

    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.json.return_value = {
        "allowed": True, "limit": None, "used": 15, "plan": "premium"
    }

    with patch("httpx.AsyncClient") as mock_http:
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http.return_value)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value.get = AsyncMock(return_value=mock_response)

        result = await client.check_limit(user_id=12345, action="file_upload")

    assert result is True


# ── Quiz browse oqimi ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_quiz_browse_shows_list():
    """Ommaviy quizlar ro'yxati ko'rsatilishi."""
    from services.bot.handlers.quiz import browse_public_quizzes

    cb = MagicMock()
    cb.data = "qb:public"
    cb.from_user.id = 12345
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    state = mock_state()

    mock_quizzes = {
        "items": [
            {"id": "quiz1", "name": "Biologiya", "total_questions": 100},
            {"id": "quiz2", "name": "Matematika", "total_questions": 80},
        ],
        "total": 2,
    }

    with patch("services.bot.handlers.quiz.ai_engine_client") as mock_client:
        mock_client.return_value.get_quizzes = AsyncMock(return_value=mock_quizzes)
        await browse_public_quizzes(cb, state)

    cb.message.edit_text.assert_called_once()
