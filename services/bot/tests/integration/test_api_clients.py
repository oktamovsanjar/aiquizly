"""
Integration testlar — bot utils/api.py klientlari.

Bu testlar real HTTP so'rovlarini mock qilib, klient logikasini tekshiradi:
  - AIEngineClient: process_file, get_quizzes
  - SubscriptionClient: check_limit (fail-open), telegram_id parametri
  - GameClient: start_game, award_xp

Real servislar bilan test uchun: INTEGRATION_REAL=1 env var qo'ying.
"""
"""
Integration testlar — bot utils/api.py klientlari.
conftest.py mock larini chetlab, utils.api ni bevosita yuklaymiz.
"""
import sys
import os
import importlib

_BOT_DIR = os.path.join(os.path.dirname(__file__), "../..")
sys.path.insert(0, _BOT_DIR)

# utils.api mock ni sys.modules dan olib tashlash — real modulni yuklaymiz
for key in list(sys.modules.keys()):
    if key in ("utils.api", "utils"):
        del sys.modules[key]

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch


# ── AIEngineClient ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ai_engine_process_file_calls_correct_endpoint():
    """/process endpoint ga POST qilinishi."""
    from utils.api import AIEngineClient

    client = AIEngineClient(base_url="http://ai-engine:8002")

    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.json.return_value = {"task_id": "abc123", "status": "processing"}

    with patch("httpx.AsyncClient") as mock_http:
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http.return_value)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value.post = AsyncMock(return_value=mock_response)

        result = await client.process_file(
            file_url="https://example.com/file.docx",
            file_name="test.docx",
            file_size=1024,
            user_id=12345,
        )

    assert result["task_id"] == "abc123"
    assert result["status"] == "processing"
    # To'g'ri endpoint chaqirildi
    call_args = mock_http.return_value.post.call_args
    assert "/process" in call_args[0][0]


@pytest.mark.asyncio
async def test_ai_engine_get_quizzes_with_pagination():
    """get_quizzes page/page_size parametrlari to'g'ri yuborilishi."""
    from utils.api import AIEngineClient

    client = AIEngineClient(base_url="http://ai-engine:8002")

    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.json.return_value = {
        "items": [{"id": "quiz1", "name": "Test Quiz"}],
        "total": 1,
        "page": 2,
    }

    with patch("httpx.AsyncClient") as mock_http:
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http.return_value)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value.get = AsyncMock(return_value=mock_response)

        result = await client.get_quizzes(page=2, page_size=5, public=True)

    assert result["page"] == 2
    params = mock_http.return_value.get.call_args[1]["params"]
    assert params["page"] == 2
    assert params["page_size"] == 5
    assert params["public"] is True


@pytest.mark.asyncio
async def test_ai_engine_service_error_raises():
    """4xx/5xx da ServiceError ko'tarilishi."""
    from utils.api import AIEngineClient, ServiceError

    client = AIEngineClient(base_url="http://ai-engine:8002")

    mock_response = MagicMock()
    mock_response.is_error = True
    mock_response.status_code = 404
    mock_response.text = '{"detail": "Not Found"}'

    with patch("httpx.AsyncClient") as mock_http:
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http.return_value)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value.post = AsyncMock(return_value=mock_response)

        with pytest.raises(ServiceError) as exc_info:
            await client.process_file(
                file_url="http://x.com/f.docx",
                file_name="f.docx",
                file_size=100,
                user_id=1,
            )

    assert exc_info.value.status == 404
    assert "ai-engine" in str(exc_info.value)


# ── SubscriptionClient ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_subscription_check_limit_allowed():
    """check_limit → True qaytarilishi."""
    from utils.api import SubscriptionClient

    client = SubscriptionClient(base_url="http://subscription:8003")

    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.json.return_value = {"allowed": True, "limit": 3, "used": 1, "plan": "free"}

    with patch("httpx.AsyncClient") as mock_http:
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http.return_value)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value.get = AsyncMock(return_value=mock_response)

        result = await client.check_limit(user_id=12345, action="file_upload")

    assert result is True
    params = mock_http.return_value.get.call_args[1]["params"]
    assert params["telegram_id"] == 12345


@pytest.mark.asyncio
async def test_subscription_check_limit_blocked():
    """check_limit → False (limitga yetdi)."""
    from utils.api import SubscriptionClient

    client = SubscriptionClient(base_url="http://subscription:8003")

    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.json.return_value = {"allowed": False, "limit": 3, "used": 3, "plan": "free"}

    with patch("httpx.AsyncClient") as mock_http:
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http.return_value)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value.get = AsyncMock(return_value=mock_response)

        result = await client.check_limit(user_id=12345, action="file_upload")

    assert result is False


@pytest.mark.asyncio
async def test_subscription_fail_open_on_error():
    """Servis xato bersa fail-open (True qaytariladi)."""
    from utils.api import SubscriptionClient

    client = SubscriptionClient(base_url="http://subscription:8003")

    with patch("httpx.AsyncClient") as mock_http:
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http.return_value)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        result = await client.check_limit(user_id=12345, action="file_upload")

    # Fail-open: xato bo'lsa ham True
    assert result is True


@pytest.mark.asyncio
async def test_subscription_fail_open_on_422():
    """422 Unprocessable Entity → fail-open."""
    from utils.api import SubscriptionClient

    client = SubscriptionClient(base_url="http://subscription:8003")

    mock_response = MagicMock()
    mock_response.is_error = True
    mock_response.status_code = 422

    with patch("httpx.AsyncClient") as mock_http:
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http.return_value)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value.get = AsyncMock(return_value=mock_response)

        result = await client.check_limit(user_id=12345, action="file_upload")

    assert result is True


# ── GameClient ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_game_client_start_game():
    """start_game POST /games ga to'g'ri body yuborishi."""
    from utils.api import GameClient

    client = GameClient(base_url="http://game:8081")

    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.json.return_value = {
        "game_id": "game-uuid-123",
        "status": "active",
        "questions": [],
    }

    with patch("httpx.AsyncClient") as mock_http:
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http.return_value)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value.post = AsyncMock(return_value=mock_response)

        result = await client.start_game(
            user_id=12345,
            quiz_id="quiz-abc",
            set_number=1,
            time_per_question=30,
        )

    assert result["game_id"] == "game-uuid-123"
    body = mock_http.return_value.post.call_args[1]["json"]
    assert body["user_id"] == 12345
    assert body["quiz_id"] == "quiz-abc"
    assert body["set_number"] == 1
    assert body["time_per_question"] == 30


@pytest.mark.asyncio
async def test_game_client_award_xp():
    """award_xp POST /users/{user_id}/xp ga to'g'ri yuborilishi."""
    from utils.api import GameClient

    client = GameClient(base_url="http://game:8081")

    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.json.return_value = {"total_xp": 150, "awarded": 50}

    with patch("httpx.AsyncClient") as mock_http:
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http.return_value)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value.post = AsyncMock(return_value=mock_response)

        result = await client.award_xp(user_id=12345, xp=50, reason="referral")

    assert result["awarded"] == 50
    url = mock_http.return_value.post.call_args[0][0]
    assert "12345" in url
    assert "/xp" in url
    body = mock_http.return_value.post.call_args[1]["json"]
    assert body["xp"] == 50
    assert body["reason"] == "referral"
