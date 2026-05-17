"""
Limit checking logic.
ONLY this module performs limit checks — nowhere else in the codebase.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from db.queries import (
    get_active_subscription,
    get_usage_count,
    increment_usage,
)
from db.models import Subscription


_REDIS_TTL_SECONDS = 35 * 24 * 3600  # 35 days — full month + buffer


class LimitChecker:
    FREE_PLAN = {
        "file_upload": 3,          # per month
        "max_questions_per_file": 50,
        "quiz_retention_days": 7,
    }

    # Actions that are counted per-month for the free plan
    COUNTED_ACTIONS = {"file_upload"}

    # ---------------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------------

    async def check(
        self,
        session: AsyncSession,
        redis: Redis,
        user_id: str,
        action: str,
    ) -> dict[str, Any]:
        """
        Check whether `user_id` is allowed to perform `action`.

        Returns:
            {
                "allowed": bool,
                "limit":   int | None,   # None = unlimited
                "used":    int,
                "plan":    str,
            }
        """
        uid = uuid.UUID(user_id)
        plan_name, subscription = await self._get_plan_info(session, uid)

        # Premium / Business — unlimited
        if plan_name in ("premium", "business"):
            return {
                "allowed": True,
                "limit": None,
                "used": 0,
                "plan": plan_name,
            }

        # Free plan — only certain actions are counted
        limit = self.FREE_PLAN.get(action)
        if limit is None:
            # Action not subject to free-plan limits
            return {
                "allowed": True,
                "limit": None,
                "used": 0,
                "plan": plan_name,
            }

        current_month = datetime.now(tz=timezone.utc).strftime("%Y-%m")
        used = await self._get_used(session, redis, uid, action, current_month)

        return {
            "allowed": used < limit,
            "limit": limit,
            "used": used,
            "plan": plan_name,
        }

    async def increment(
        self,
        session: AsyncSession,
        redis: Redis,
        user_id: str,
        action: str,
    ) -> None:
        """
        Increment usage counter for `action` in both Redis and DB.
        Should be called after a successful action, not before.
        """
        uid = uuid.UUID(user_id)
        current_month = datetime.now(tz=timezone.utc).strftime("%Y-%m")

        # 1. Redis fast counter
        redis_key = self._redis_key(user_id, action, current_month)
        await redis.incr(redis_key)
        await redis.expire(redis_key, _REDIS_TTL_SECONDS)

        # 2. Persistent DB log (upsert)
        await increment_usage(session, uid, action, current_month)

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    async def _get_plan_info(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> tuple[str, Subscription | None]:
        """Return (plan_name, subscription_or_None)."""
        subscription = await get_active_subscription(session, user_id)
        if subscription is None:
            return "free", None

        # Eager-load plan name via relationship (already loaded by joined query)
        # The plan relationship is lazy by default; refresh if needed.
        if subscription.plan is None:
            await session.refresh(subscription, ["plan"])

        plan_name = subscription.plan.name if subscription.plan else "free"
        return plan_name, subscription

    async def _get_used(
        self,
        session: AsyncSession,
        redis: Redis,
        user_id: uuid.UUID,
        action: str,
        month: str,
    ) -> int:
        """
        Read usage counter from Redis first (fast path).
        Fall back to DB if Redis key does not exist (e.g. after restart),
        then warm the Redis cache.
        """
        redis_key = self._redis_key(str(user_id), action, month)
        cached = await redis.get(redis_key)

        if cached is not None:
            return int(cached)

        # Cache miss — read from DB
        db_count = await get_usage_count(session, user_id, action, month)

        if db_count > 0:
            # Warm the cache
            await redis.set(redis_key, db_count, ex=_REDIS_TTL_SECONDS)

        return db_count

    @staticmethod
    def _redis_key(user_id: str, action: str, month: str) -> str:
        return f"usage:{user_id}:{action}:{month}"
