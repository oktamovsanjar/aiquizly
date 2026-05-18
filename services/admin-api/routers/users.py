"""Foydalanuvchilar boshqaruvi."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from deps import require_auth, get_db
from models import User, Quiz, Payment, Subscription

router = APIRouter(prefix="/users", tags=["users"])


def _user_dict(u: User) -> dict:
    return {
        "id": str(u.id),
        "telegram_id": u.telegram_id,
        "username": u.username,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "language_code": u.language_code,
        "is_bot_blocked": u.is_bot_blocked,
        "last_active_at": u.last_active_at.isoformat() if u.last_active_at else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@router.get("", dependencies=[Depends(require_auth)])
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(50, le=200),
    search: Optional[str] = Query(
        None, description="Username yoki telegram_id bo'yicha qidirish"
    ),
    is_blocked: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit
    stmt = select(User)
    count_stmt = select(func.count()).select_from(User)

    if search:
        try:
            tg_id = int(search)
            filter_clause = or_(
                User.telegram_id == tg_id, User.username.ilike(f"%{search}%")
            )
        except ValueError:
            filter_clause = User.username.ilike(f"%{search}%")
        stmt = stmt.where(filter_clause)
        count_stmt = count_stmt.where(filter_clause)

    if is_blocked is not None:
        stmt = stmt.where(User.is_bot_blocked.is_(is_blocked))
        count_stmt = count_stmt.where(User.is_bot_blocked.is_(is_blocked))

    total = (await db.execute(count_stmt)).scalar() or 0
    users = (
        (
            await db.execute(
                stmt.order_by(User.created_at.desc()).offset(offset).limit(limit)
            )
        )
        .scalars()
        .all()
    )

    return {
        "users": [_user_dict(u) for u in users],
        "total": total,
        "page": page,
        "pages": max(1, (total + limit - 1) // limit),
    }


@router.get("/{user_id}", dependencies=[Depends(require_auth)])
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    import uuid as uuid_mod

    user = (
        await db.execute(select(User).where(User.id == uuid_mod.UUID(user_id)))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

    # Qo'shimcha ma'lumotlar
    quiz_count = (
        await db.execute(
            select(func.count())
            .select_from(Quiz)
            .where(Quiz.owner_id == user.id, Quiz.deleted_at.is_(None))
        )
    ).scalar() or 0

    sub = (
        await db.execute(
            select(Subscription)
            .where(Subscription.user_id == user.id, Subscription.status == "active")
            .order_by(Subscription.started_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    total_paid = (
        await db.execute(
            select(func.sum(Payment.amount)).where(
                Payment.user_id == user.id, Payment.status == "completed"
            )
        )
    ).scalar() or 0

    data = _user_dict(user)
    data["quiz_count"] = quiz_count
    data["total_paid_uzs"] = total_paid
    data["subscription"] = (
        {
            "status": sub.status,
            "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
        }
        if sub
        else None
    )
    return data


@router.patch("/{user_id}/block", dependencies=[Depends(require_auth)])
async def toggle_block(user_id: str, db: AsyncSession = Depends(get_db)):
    """Foydalanuvchini bloklash / blokdan chiqarish."""
    import uuid as uuid_mod

    user = (
        await db.execute(select(User).where(User.id == uuid_mod.UUID(user_id)))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

    new_status = not user.is_bot_blocked
    await db.execute(
        update(User)
        .where(User.id == uuid_mod.UUID(user_id))
        .values(is_bot_blocked=new_status, updated_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"user_id": user_id, "is_bot_blocked": new_status}
