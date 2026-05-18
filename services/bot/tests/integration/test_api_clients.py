"""
Integration testlar — bot utils/api.py klientlari.

Har bir klient uchun `client._http` ni to'g'ridan-to'g'ri mock qilamiz —
shunday qilib real HTTP so'rovlari yuborilmaydi.
"""

import sys
import os

_BOT_DIR = os.path.join(os.path.dirname(__file__), "../..")
sys.path.insert(0, _BOT_DIR)

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock


def _make_resp(json_data: dict, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.is_error = status >= 400
    resp.status_code = status
    resp.json.return_value = json_data
    resp.text = str(json_data)
    return resp


# ── AIEngineClient ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ai_engine_process_file_calls_correct_endpoint():
    """/process endpoint ga POST qilinishi."""
    from utils.api import AIEngineClient

    client = AIEngineClient(base_url="http://ai-engine:8002")
    client._http = MagicMock()
    client._http.post = AsyncMock(
        return_value=_make_resp({"task_id": "abc123", "status": "processing"})
    )

    result = await client.process_file(
        file_url="https://example.com/file.docx",
        file_name="test.docx",
        file_size=1024,
        user_id=12345,
    )

    assert result["task_id"] == "abc123"
    assert result["status"] == "processing"
    url = client._http.post.call_args[0][0]
    assert "/process" in url


@pytest.mark.asyncio
async def test_ai_engine_get_quizzes_with_pagination():
    """get_quizzes limit/offset parametrlari to'g'ri yuborilishi."""
    from utils.api import AIEngineClient

    client = AIEngineClient(base_url="http://ai-engine:8002")
    client._http = MagicMock()
    client._http.get = AsyncMock(
        return_value=_make_resp({"quizzes": [{"id": "quiz1"}], "total": 1})
    )

    result = await client.get_quizzes(page=2, page_size=5, public=True)

    assert "quizzes" in result
    params = client._http.get.call_args[1]["params"]
    assert params["limit"] == 5
    assert params["offset"] == 5  # (page-1) * page_size = 1 * 5
    assert params["visibility"] == "public"


@pytest.mark.asyncio
async def test_ai_engine_service_error_raises():
    """4xx/5xx da ServiceError ko'tarilishi."""
    from utils.api import AIEngineClient, ServiceError

    client = AIEngineClient(base_url="http://ai-engine:8002")
    client._http = MagicMock()
    client._http.post = AsyncMock(
        return_value=_make_resp({"detail": "Not Found"}, status=404)
    )

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
    client._http = MagicMock()
    client._http.get = AsyncMock(
        return_value=_make_resp(
            {"allowed": True, "limit": 3, "used": 1, "plan": "free"}
        )
    )

    result = await client.check_limit(user_id=12345, action="file_upload")

    assert result is True
    params = client._http.get.call_args[1]["params"]
    assert params["telegram_id"] == 12345
    assert params["action"] == "file_upload"


@pytest.mark.asyncio
async def test_subscription_check_limit_blocked():
    """check_limit → False (limitga yetdi)."""
    from utils.api import SubscriptionClient

    client = SubscriptionClient(base_url="http://subscription:8003")
    client._http = MagicMock()
    client._http.get = AsyncMock(
        return_value=_make_resp(
            {"allowed": False, "limit": 3, "used": 3, "plan": "free"}
        )
    )

    result = await client.check_limit(user_id=12345, action="file_upload")

    assert result is False


@pytest.mark.asyncio
async def test_subscription_fail_open_on_error():
    """Servis xato bersa fail-open (True qaytariladi)."""
    from utils.api import SubscriptionClient

    client = SubscriptionClient(base_url="http://subscription:8003")
    client._http = MagicMock()
    client._http.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

    result = await client.check_limit(user_id=12345, action="file_upload")

    assert result is True


@pytest.mark.asyncio
async def test_subscription_fail_open_on_422():
    """422 → fail-open."""
    from utils.api import SubscriptionClient

    client = SubscriptionClient(base_url="http://subscription:8003")
    client._http = MagicMock()
    client._http.get = AsyncMock(return_value=_make_resp({}, status=422))

    result = await client.check_limit(user_id=12345, action="file_upload")

    assert result is True


# ── GameClient ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_game_client_start_game():
    """start_game POST /games ga to'g'ri body yuborishi."""
    from utils.api import GameClient

    client = GameClient(base_url="http://game:8081")
    client._http = MagicMock()
    client._http.post = AsyncMock(
        return_value=_make_resp({"game_id": "game-uuid-123", "status": "active"})
    )

    result = await client.start_game(
        user_id=12345,
        quiz_id="quiz-abc",
        set_number=1,
        time_per_question=30,
    )

    assert result["game_id"] == "game-uuid-123"
    body = client._http.post.call_args[1]["json"]
    assert body["user_id"] == 12345
    assert body["quiz_id"] == "quiz-abc"
    assert body["set_number"] == 1
    assert body["time_per_question"] == 30


@pytest.mark.asyncio
async def test_game_client_award_xp():
    """award_xp POST /users/{user_id}/xp ga to'g'ri yuborilishi."""
    from utils.api import GameClient

    client = GameClient(base_url="http://game:8081")
    client._http = MagicMock()
    client._http.post = AsyncMock(
        return_value=_make_resp({"total_xp": 150, "awarded": 50})
    )

    result = await client.award_xp(user_id=12345, xp=50, reason="referral")

    assert result["awarded"] == 50
    url = client._http.post.call_args[0][0]
    assert "12345" in url
    assert "/xp" in url
    body = client._http.post.call_args[1]["json"]
    assert body["xp"] == 50
    assert body["reason"] == "referral"
