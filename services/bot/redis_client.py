"""
Async Redis client.

DB layout (all on DB 1):
  session:{user_id}          → JSON user state / language / current flow
  game:{game_id}             → JSON current game state
  voting:{chat_id}:{msg_id}  → JSON voting state for a Telegram group quiz
"""
from __future__ import annotations

import json
import os
from typing import Any

import redis.asyncio as aioredis

REDIS_URL: str = os.environ.get("REDIS_URL", "redis://redis:6379/1")

_redis_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Return the module-level Redis client (lazy-init)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


# ──────────────────────────── Session State ────────────────────────────


async def get_session_state(user_id: int) -> dict[str, Any]:
    """Return the user's session state dict, or empty dict if not set."""
    r = get_redis()
    raw = await r.get(f"session:{user_id}")
    if raw is None:
        return {}
    return json.loads(raw)


async def set_session_state(user_id: int, state: dict[str, Any], ttl: int = 86400) -> None:
    """Persist user session state with a TTL (default 24 h)."""
    r = get_redis()
    await r.set(f"session:{user_id}", json.dumps(state), ex=ttl)


async def delete_session_state(user_id: int) -> None:
    r = get_redis()
    await r.delete(f"session:{user_id}")


# ──────────────────────────── Game State ────────────────────────────


async def get_game_state(game_id: str) -> dict[str, Any] | None:
    r = get_redis()
    raw = await r.get(f"game:{game_id}")
    if raw is None:
        return None
    return json.loads(raw)


async def set_game_state(game_id: str, state: dict[str, Any], ttl: int = 7200) -> None:
    """Persist game state. Default TTL 2 hours."""
    r = get_redis()
    await r.set(f"game:{game_id}", json.dumps(state), ex=ttl)


async def delete_game_state(game_id: str) -> None:
    r = get_redis()
    await r.delete(f"game:{game_id}")


# ──────────────────────────── Voting State ────────────────────────────


async def get_voting_state(chat_id: int, msg_id: int) -> dict[str, Any] | None:
    r = get_redis()
    raw = await r.get(f"voting:{chat_id}:{msg_id}")
    if raw is None:
        return None
    return json.loads(raw)


async def set_voting_state(
    chat_id: int, msg_id: int, state: dict[str, Any], ttl: int = 120
) -> None:
    """Voting state expires after 2 minutes by default."""
    r = get_redis()
    await r.set(f"voting:{chat_id}:{msg_id}", json.dumps(state), ex=ttl)


async def delete_voting_state(chat_id: int, msg_id: int) -> None:
    r = get_redis()
    await r.delete(f"voting:{chat_id}:{msg_id}")


# ──────────────────────────── Image Upload Buffer ────────────────────────────
# Temporary buffer for multi-image upload (quiz creation from photos).
# Key: image_buffer:{user_id}  Value: JSON list of file_ids


async def get_image_buffer(user_id: int) -> list[str]:
    r = get_redis()
    raw = await r.get(f"image_buffer:{user_id}")
    if raw is None:
        return []
    return json.loads(raw)


async def append_image_buffer(user_id: int, file_id: str, ttl: int = 3600) -> int:
    """Append a file_id to the user's image buffer. Returns new length."""
    r = get_redis()
    key = f"image_buffer:{user_id}"
    current = await get_image_buffer(user_id)
    current.append(file_id)
    await r.set(key, json.dumps(current), ex=ttl)
    return len(current)


async def clear_image_buffer(user_id: int) -> None:
    r = get_redis()
    await r.delete(f"image_buffer:{user_id}")


# ──────────────────────────── Manual Quiz Buffer ────────────────────────────
# Key: manual_quiz:{user_id}  Value: JSON dict with in-progress quiz data


async def get_manual_quiz(user_id: int) -> dict[str, Any]:
    r = get_redis()
    raw = await r.get(f"manual_quiz:{user_id}")
    if raw is None:
        return {}
    return json.loads(raw)


async def set_manual_quiz(user_id: int, data: dict[str, Any], ttl: int = 3600) -> None:
    r = get_redis()
    await r.set(f"manual_quiz:{user_id}", json.dumps(data), ex=ttl)


async def clear_manual_quiz(user_id: int) -> None:
    r = get_redis()
    await r.delete(f"manual_quiz:{user_id}")


# ──────────────────────────── Close ────────────────────────────


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
