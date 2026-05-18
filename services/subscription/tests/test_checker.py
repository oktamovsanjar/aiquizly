"""
LimitChecker unit testlar — DB va Redis mock bilan.

Testlar checker.py mantiqini tekshiradi:
  - Free plan limiti (3 ta fayl/oy)
  - Premium/business — unlimited
  - Redis cache miss → DB fallback
  - Increment logikasi
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from limits.checker import LimitChecker

# ──────────────────────────── Fixtures ────────────────────────────


def make_checker():
    return LimitChecker()


def mock_session():
    return AsyncMock()


def mock_redis(cached_value=None):
    r = AsyncMock()
    r.get = AsyncMock(return_value=cached_value)
    r.set = AsyncMock()
    r.incr = AsyncMock(return_value=1)
    r.expire = AsyncMock()
    return r


# ──────────────────────────── check() testlar ────────────────────────────


@pytest.mark.asyncio
async def test_check_free_plan_under_limit():
    """Free plan, foydalanuvchi 2 ta yuklagan, limit 3 — ruxsat berilishi kerak."""
    checker = make_checker()
    session = mock_session()
    redis = mock_redis(cached_value=b"2")  # Redis cache: 2 ta ishlatilgan

    user_id = str(uuid.uuid4())

    with patch(
        "limits.checker.get_active_subscription", new_callable=AsyncMock
    ) as mock_sub:
        mock_sub.return_value = None  # Free plan
        result = await checker.check(session, redis, user_id, "file_upload")

    assert result["allowed"] is True
    assert result["limit"] == 3
    assert result["used"] == 2
    assert result["plan"] == "free"


@pytest.mark.asyncio
async def test_check_free_plan_at_limit():
    """Free plan, foydalanuvchi 3 ta yuklagan — bloklash kerak."""
    checker = make_checker()
    session = mock_session()
    redis = mock_redis(cached_value=b"3")

    user_id = str(uuid.uuid4())

    with patch(
        "limits.checker.get_active_subscription", new_callable=AsyncMock
    ) as mock_sub:
        mock_sub.return_value = None
        result = await checker.check(session, redis, user_id, "file_upload")

    assert result["allowed"] is False
    assert result["used"] == 3
    assert result["limit"] == 3


@pytest.mark.asyncio
async def test_check_premium_unlimited():
    """Premium plan — har qanday limitda ruxsat."""
    checker = make_checker()
    session = mock_session()
    redis = mock_redis()

    user_id = str(uuid.uuid4())

    # Premium subscription mock
    mock_subscription = MagicMock()
    mock_plan = MagicMock()
    mock_plan.name = "premium"
    mock_subscription.plan = mock_plan

    with patch(
        "limits.checker.get_active_subscription", new_callable=AsyncMock
    ) as mock_sub:
        mock_sub.return_value = mock_subscription
        result = await checker.check(session, redis, user_id, "file_upload")

    assert result["allowed"] is True
    assert result["limit"] is None
    assert result["plan"] == "premium"


@pytest.mark.asyncio
async def test_check_business_unlimited():
    """Business plan — unlimited."""
    checker = make_checker()
    session = mock_session()
    redis = mock_redis()

    user_id = str(uuid.uuid4())

    mock_subscription = MagicMock()
    mock_plan = MagicMock()
    mock_plan.name = "business"
    mock_subscription.plan = mock_plan

    with patch(
        "limits.checker.get_active_subscription", new_callable=AsyncMock
    ) as mock_sub:
        mock_sub.return_value = mock_subscription
        result = await checker.check(session, redis, user_id, "file_upload")

    assert result["allowed"] is True
    assert result["limit"] is None
    assert result["plan"] == "business"


@pytest.mark.asyncio
async def test_check_unknown_action_allowed():
    """Noma'lum action — limit yo'q, ruxsat."""
    checker = make_checker()
    session = mock_session()
    redis = mock_redis()

    user_id = str(uuid.uuid4())

    with patch(
        "limits.checker.get_active_subscription", new_callable=AsyncMock
    ) as mock_sub:
        mock_sub.return_value = None  # Free plan
        result = await checker.check(session, redis, user_id, "unknown_action")

    assert result["allowed"] is True
    assert result["limit"] is None


@pytest.mark.asyncio
async def test_check_redis_cache_miss_fallback_to_db():
    """Redis miss bo'lsa DB dan o'qiladi va cache isitiladi."""
    checker = make_checker()
    session = mock_session()
    redis = mock_redis(cached_value=None)  # Cache miss

    user_id = str(uuid.uuid4())

    with patch(
        "limits.checker.get_active_subscription", new_callable=AsyncMock
    ) as mock_sub:
        mock_sub.return_value = None
        with patch(
            "limits.checker.get_usage_count", new_callable=AsyncMock
        ) as mock_count:
            mock_count.return_value = 1  # DB da 1 ta
            result = await checker.check(session, redis, user_id, "file_upload")

    assert result["used"] == 1
    assert result["allowed"] is True
    # Cache isitildi
    redis.set.assert_called_once()


# ──────────────────────────── increment() testlar ────────────────────────────


@pytest.mark.asyncio
async def test_increment_updates_redis_and_db():
    """Increment Redis va DB ikkalasini ham yangilaydi."""
    checker = make_checker()
    session = mock_session()
    redis = mock_redis()

    user_id = str(uuid.uuid4())

    with patch("limits.checker.increment_usage", new_callable=AsyncMock) as mock_incr:
        await checker.increment(session, redis, user_id, "file_upload")
        mock_incr.assert_called_once()

    redis.incr.assert_called_once()
    redis.expire.assert_called_once()


@pytest.mark.asyncio
async def test_redis_key_format():
    """Redis key formati to'g'ri."""
    user_id = "abc123"
    action = "file_upload"
    month = "2026-05"

    key = LimitChecker._redis_key(user_id, action, month)
    assert key == f"usage:{user_id}:{action}:{month}"


# ──────────────────────────── FREE_PLAN constants ────────────────────────────


def test_free_plan_limits():
    checker = LimitChecker()
    assert checker.FREE_PLAN["file_upload"] == 3
    assert "file_upload" in checker.COUNTED_ACTIONS
