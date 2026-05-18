"""Analytics — statistika va o'sish ko'rsatkichlari."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from deps import require_auth, get_db
from models import User, Quiz, Payment, Subscription

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", dependencies=[Depends(require_auth)])
async def overview(db: AsyncSession = Depends(get_db)):
    """Asosiy ko'rsatkichlar: foydalanuvchilar, quizlar, daromad."""
    now = datetime.now(timezone.utc)
    month_ago = now - timedelta(days=30)
    week_ago = now - timedelta(days=7)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_users = (
        await db.execute(select(func.count()).select_from(User))
    ).scalar() or 0
    new_users_week = (
        await db.execute(
            select(func.count()).select_from(User).where(User.created_at >= week_ago)
        )
    ).scalar() or 0
    new_users_today = (
        await db.execute(
            select(func.count()).select_from(User).where(User.created_at >= today)
        )
    ).scalar() or 0
    active_users_week = (
        await db.execute(
            select(func.count())
            .select_from(User)
            .where(User.last_active_at >= week_ago)
        )
    ).scalar() or 0
    blocked_users = (
        await db.execute(
            select(func.count()).select_from(User).where(User.is_bot_blocked.is_(True))
        )
    ).scalar() or 0

    total_quizzes = (
        await db.execute(
            select(func.count()).select_from(Quiz).where(Quiz.deleted_at.is_(None))
        )
    ).scalar() or 0
    public_quizzes = (
        await db.execute(
            select(func.count())
            .select_from(Quiz)
            .where(Quiz.deleted_at.is_(None), Quiz.visibility == "public")
        )
    ).scalar() or 0
    quizzes_week = (
        await db.execute(
            select(func.count())
            .select_from(Quiz)
            .where(Quiz.deleted_at.is_(None), Quiz.created_at >= week_ago)
        )
    ).scalar() or 0

    active_subs = (
        await db.execute(
            select(func.count())
            .select_from(Subscription)
            .where(Subscription.status == "active")
        )
    ).scalar() or 0

    total_revenue = (
        await db.execute(
            select(func.sum(Payment.amount)).where(Payment.status == "completed")
        )
    ).scalar() or 0
    revenue_month = (
        await db.execute(
            select(func.sum(Payment.amount)).where(
                Payment.status == "completed", Payment.created_at >= month_ago
            )
        )
    ).scalar() or 0

    return {
        "users": {
            "total": total_users,
            "new_today": new_users_today,
            "new_this_week": new_users_week,
            "active_this_week": active_users_week,
            "blocked": blocked_users,
        },
        "quizzes": {
            "total": total_quizzes,
            "public": public_quizzes,
            "private": total_quizzes - public_quizzes,
            "new_this_week": quizzes_week,
        },
        "subscriptions": {
            "active": active_subs,
        },
        "revenue": {
            "total_uzs": total_revenue,
            "this_month_uzs": revenue_month,
        },
    }


@router.get("/growth", dependencies=[Depends(require_auth)])
async def growth(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Kunlik o'sish grafigi — foydalanuvchilar va quizlar."""
    result = await db.execute(text("""
        SELECT
            date_trunc('day', created_at)::date AS day,
            COUNT(*) AS new_users
        FROM users
        WHERE created_at >= NOW() - INTERVAL ':days days'
        GROUP BY day
        ORDER BY day
    """).bindparams(days=days))
    user_rows = result.fetchall()

    result2 = await db.execute(text("""
        SELECT
            date_trunc('day', created_at)::date AS day,
            COUNT(*) AS new_quizzes
        FROM quizzes
        WHERE created_at >= NOW() - INTERVAL ':days days'
          AND deleted_at IS NULL
        GROUP BY day
        ORDER BY day
    """).bindparams(days=days))
    quiz_rows = result2.fetchall()

    user_map = {str(r.day): r.new_users for r in user_rows}
    quiz_map = {str(r.day): r.new_quizzes for r in quiz_rows}

    all_days = sorted(set(list(user_map.keys()) + list(quiz_map.keys())))

    return {
        "days": days,
        "data": [
            {
                "date": d,
                "new_users": user_map.get(d, 0),
                "new_quizzes": quiz_map.get(d, 0),
            }
            for d in all_days
        ],
    }


@router.get("/revenue", dependencies=[Depends(require_auth)])
async def revenue_stats(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Kunlik daromad va to'lovlar."""
    result = await db.execute(text("""
        SELECT
            date_trunc('day', created_at)::date AS day,
            SUM(amount) AS total_amount,
            COUNT(*) AS payment_count,
            provider
        FROM payments
        WHERE status = 'completed'
          AND created_at >= NOW() - INTERVAL ':days days'
        GROUP BY day, provider
        ORDER BY day
    """).bindparams(days=days))
    rows = result.fetchall()

    return {
        "days": days,
        "data": [
            {
                "date": str(r.day),
                "amount_uzs": r.total_amount or 0,
                "count": r.payment_count,
                "provider": r.provider,
            }
            for r in rows
        ],
    }


@router.get("/imports", dependencies=[Depends(require_auth)])
async def import_stats(db: AsyncSession = Depends(get_db)):
    """AI fayl qayta ishlash statistikasi."""
    result = await db.execute(text("""
        SELECT
            status,
            file_type,
            COUNT(*) AS count,
            AVG(processing_time_ms) AS avg_ms,
            AVG(total_imported) AS avg_questions
        FROM import_logs
        GROUP BY status, file_type
        ORDER BY count DESC
    """))
    rows = result.fetchall()

    return {
        "breakdown": [
            {
                "status": r.status,
                "file_type": r.file_type,
                "count": r.count,
                "avg_processing_ms": round(r.avg_ms or 0),
                "avg_questions": round(r.avg_questions or 0, 1),
            }
            for r in rows
        ]
    }
