"""User sozlamalarini Redis da saqlash va o'qish."""
import json
from redis_client import get_redis

_KEY = "user_settings:{}"
_TTL = 86400 * 365  # 1 yil


async def get_user_settings(telegram_id: int) -> dict:
    r = get_redis()
    raw = await r.get(_KEY.format(telegram_id))
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    return {}


async def save_user_settings(telegram_id: int, settings: dict) -> None:
    r = get_redis()
    await r.set(_KEY.format(telegram_id), json.dumps(settings), ex=_TTL)


async def update_user_setting(telegram_id: int, key: str, value) -> None:
    settings = await get_user_settings(telegram_id)
    settings[key] = value
    await save_user_settings(telegram_id, settings)
