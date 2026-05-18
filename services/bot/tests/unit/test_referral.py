"""
Referral bonus logikasi unit testlar.
Mock infratuzilma conftest.py da tayyorlanadi.

Testlar _process_referral() ni tekshiradi:
  - O'z-o'ziga referral bloklash
  - Referrer DB da yo'q bo'lsa None
  - To'g'ri referral: nom qaytariladi, DB ga yoziladi
  - Dublikat: ikkinchi marta None
  - Servis fail bo'lsa ham fail-open
"""

import sys
import os
import importlib.util

# handlers/__init__.py ni chetlab, faqat start.py ni yuklash
_BOT_DIR = os.path.join(os.path.dirname(__file__), "../..")
sys.path.insert(0, _BOT_DIR)


# handlers paketi sifatida yuklamaslik uchun — to'g'ridan spec yuklaymiz
def _load_start_module():
    spec = importlib.util.spec_from_file_location(
        "handlers_start_isolated",
        os.path.join(_BOT_DIR, "handlers", "start.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["handlers_start_isolated"] = mod
    spec.loader.exec_module(mod)
    return mod


import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ── Helpers ───────────────────────────────────────────────────────────────────


def make_user(telegram_id: int, user_id=None):
    u = MagicMock()
    u.id = user_id or uuid.uuid4()
    u.telegram_id = telegram_id
    u.first_name = "Test"
    u.username = "testuser"
    u.referred_by = None
    return u


def make_session(call_results: list):
    """call_results: har execute() chaqiruvida qaytariladigan scalar qiymatlar."""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.get = AsyncMock(return_value=MagicMock(referred_by=None))

    call_iter = iter(call_results)

    async def mock_execute(*args, **kwargs):
        result = MagicMock()
        try:
            result.scalar_one_or_none.return_value = next(call_iter)
        except StopIteration:
            result.scalar_one_or_none.return_value = None
        return result

    session.execute = mock_execute
    return session


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_self_referral_blocked():
    """Foydalanuvchi o'z linkini ishlatsa bonus berilmaydi."""
    from handlers.start import _process_referral

    user = make_user(telegram_id=12345)
    result = await _process_referral(user, referrer_telegram_id=12345)
    assert result is None


@pytest.mark.asyncio
async def test_referrer_not_found_returns_none():
    """Referrer DB da yo'q → None."""
    from handlers.start import _process_referral

    user = make_user(telegram_id=11111)
    session = make_session([None])  # referrer topilmadi

    with patch("handlers.start.AsyncSessionLocal", return_value=session):
        result = await _process_referral(user, referrer_telegram_id=99999)

    assert result is None


@pytest.mark.asyncio
async def test_valid_referral_returns_name():
    """To'g'ri referral — referrer nomi qaytariladi."""
    from handlers.start import _process_referral

    referred = make_user(telegram_id=22222)
    referrer = make_user(telegram_id=33333)
    referrer.first_name = "Aziz"

    session = make_session([referrer, None])  # referrer topildi, dublikat yo'q

    with patch("handlers.start.AsyncSessionLocal", return_value=session):
        with patch("utils.api.subscription_client") as mock_sub:
            mock_sub.return_value.activate_premium = AsyncMock()
            with patch("utils.api.game_client") as mock_game:
                mock_game.return_value.award_xp = AsyncMock()
                result = await _process_referral(referred, referrer_telegram_id=33333)

    assert result == "Aziz"


@pytest.mark.asyncio
async def test_duplicate_referral_returns_none():
    """Dublikat referral → None."""
    from handlers.start import _process_referral

    referred = make_user(telegram_id=44444)
    referrer = make_user(telegram_id=55555)
    existing_dup = MagicMock()  # Dublikat topildi

    session = make_session([referrer, existing_dup])

    with patch("handlers.start.AsyncSessionLocal", return_value=session):
        result = await _process_referral(referred, referrer_telegram_id=55555)

    assert result is None


@pytest.mark.asyncio
async def test_referral_works_even_if_xp_service_fails():
    """Servis xato bersa ham referral yozuvi saqlanadi (fail-open)."""
    from handlers.start import _process_referral

    referred = make_user(telegram_id=66666)
    referrer = make_user(telegram_id=77777)
    referrer.first_name = "Madina"

    session = make_session([referrer, None])

    with patch("handlers.start.AsyncSessionLocal", return_value=session):
        with patch("utils.api.subscription_client") as mock_sub:
            mock_sub.return_value.activate_premium = AsyncMock(
                side_effect=Exception("xato")
            )
            with patch("utils.api.game_client") as mock_game:
                mock_game.return_value.award_xp = AsyncMock(
                    side_effect=Exception("xato")
                )
                result = await _process_referral(referred, referrer_telegram_id=77777)

    # Xato bo'lsa ham nom qaytariladi
    assert result == "Madina"


# ── Constants ─────────────────────────────────────────────────────────────────


def test_referral_xp_constants():
    from handlers.start import (
        REFERRAL_XP_REFERRER,
        REFERRAL_XP_REFERRED,
        REFERRAL_PREMIUM_DAYS,
    )

    assert REFERRAL_XP_REFERRER == 50
    assert REFERRAL_XP_REFERRED == 20
    assert REFERRAL_PREMIUM_DAYS == 3
