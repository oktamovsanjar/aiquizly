"""
All async DB operations for the subscription service.
Uses SQLAlchemy 2.0 async style throughout.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .models import Plan, Subscription, Payment, UsageLog


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------

async def get_active_subscription(
    session: AsyncSession, user_id: uuid.UUID
) -> Optional[Subscription]:
    """Return the user's currently active subscription, or None."""
    now = datetime.now(tz=timezone.utc)
    result = await session.execute(
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.status == "active",
            (Subscription.expires_at.is_(None) | (Subscription.expires_at > now)),
        )
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    return result.scalars().first()


async def create_subscription(
    session: AsyncSession,
    user_id: uuid.UUID,
    plan_id: uuid.UUID,
    days: int,
) -> Subscription:
    """Create a new active subscription starting now, lasting `days` days."""
    now = datetime.now(tz=timezone.utc)
    expires_at = now + timedelta(days=days) if days > 0 else None
    subscription = Subscription(
        user_id=user_id,
        plan_id=plan_id,
        status="active",
        started_at=now,
        expires_at=expires_at,
        auto_renew=True,
    )
    session.add(subscription)
    await session.flush()  # populate .id without committing
    return subscription


async def expire_subscriptions(session: AsyncSession) -> int:
    """
    Mark all subscriptions whose expires_at has passed as 'expired'.
    Returns the count of rows updated.
    """
    now = datetime.now(tz=timezone.utc)
    result = await session.execute(
        update(Subscription)
        .where(
            Subscription.status == "active",
            Subscription.expires_at.isnot(None),
            Subscription.expires_at <= now,
        )
        .values(status="expired", updated_at=now)
    )
    return result.rowcount


async def add_bonus_days(
    session: AsyncSession, user_id: uuid.UUID, days: int
) -> None:
    """
    Extend the user's active subscription by `days` days.
    If no active subscription exists, create a free-plan entry.
    """
    subscription = await get_active_subscription(session, user_id)
    now = datetime.now(tz=timezone.utc)

    if subscription is not None:
        base = subscription.expires_at if subscription.expires_at and subscription.expires_at > now else now
        await session.execute(
            update(Subscription)
            .where(Subscription.id == subscription.id)
            .values(expires_at=base + timedelta(days=days), updated_at=now)
        )
    else:
        # Fetch the free plan to attach bonus days to it
        free_plan = await get_plan(session, "free")
        if free_plan is None:
            return
        new_sub = Subscription(
            user_id=user_id,
            plan_id=free_plan.id,
            status="active",
            started_at=now,
            expires_at=now + timedelta(days=days),
            auto_renew=False,
        )
        session.add(new_sub)
        await session.flush()


# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------

async def get_plan(session: AsyncSession, plan_name: str) -> Optional[Plan]:
    """Return a plan by name (e.g. 'free', 'premium', 'business')."""
    result = await session.execute(
        select(Plan).where(Plan.name == plan_name, Plan.is_active.is_(True))
    )
    return result.scalars().first()


async def get_all_active_plans(session: AsyncSession) -> list[Plan]:
    """Return all active plans ordered by price ascending."""
    result = await session.execute(
        select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price_monthly)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

async def create_payment(
    session: AsyncSession,
    user_id: uuid.UUID,
    subscription_id: Optional[uuid.UUID],
    provider: str,
    amount: int,
    currency: str,
    provider_payment_id: Optional[str],
) -> Payment:
    """Create a pending payment record."""
    payment = Payment(
        user_id=user_id,
        subscription_id=subscription_id,
        provider=provider,
        provider_payment_id=provider_payment_id,
        amount=amount,
        currency=currency,
        status="pending",
    )
    session.add(payment)
    await session.flush()
    return payment


async def complete_payment(
    session: AsyncSession,
    payment_id: uuid.UUID,
    provider_payment_id: str,
) -> None:
    """Mark a payment as completed and store the provider's payment ID."""
    await session.execute(
        update(Payment)
        .where(Payment.id == payment_id)
        .values(status="completed", provider_payment_id=provider_payment_id)
    )


async def get_payments(
    session: AsyncSession,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Payment]:
    """Return payments filtered by optional status."""
    stmt = select(Payment).order_by(Payment.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(Payment.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Usage logs
# ---------------------------------------------------------------------------

async def get_usage_count(
    session: AsyncSession,
    user_id: uuid.UUID,
    action: str,
    month: str,
) -> int:
    """Return how many times `action` was performed in `month` (e.g. '2026-05')."""
    result = await session.execute(
        select(UsageLog.count).where(
            UsageLog.user_id == user_id,
            UsageLog.action == action,
            UsageLog.month == month,
        )
    )
    row = result.scalar_one_or_none()
    return row if row is not None else 0


async def increment_usage(
    session: AsyncSession,
    user_id: uuid.UUID,
    action: str,
    month: str,
) -> None:
    """
    Upsert usage log: INSERT ... ON CONFLICT DO UPDATE SET count = count + 1.
    Guarantees atomicity without a SELECT-then-UPDATE race condition.
    """
    stmt = pg_insert(UsageLog).values(
        id=uuid.uuid4(),
        user_id=user_id,
        action=action,
        month=month,
        count=1,
        created_at=datetime.now(tz=timezone.utc),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "action", "month"],
        set_={"count": UsageLog.count + 1},
    )
    await session.execute(stmt)
