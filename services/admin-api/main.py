"""Admin API — quiz bot tizim boshqaruvi."""
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Header, Query
from pydantic import BaseModel
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from models import Admin, Setting, User, Quiz, Subscription, Payment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "admin-secret-change-me")

engine = create_async_engine(
    DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    pool_size=5,
    echo=False,
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _require_auth(x_admin_token: str = Header(None)):
    if x_admin_token != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Admin token xato")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Admin API ishga tushdi")
    yield
    await engine.dispose()
    logger.info("Admin API to'xtatildi")


app = FastAPI(title="Quiz Bot Admin API", lifespan=lifespan)


# ─────────────────────────── Health ───────────────────────────

@app.get("/health")
async def health():
    db_status = "ok"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return {
        "status": "healthy",
        "service": "admin-api",
        "version": "1.0.0",
        "checks": {"database": db_status},
    }


# ─────────────────────────── Statistika ───────────────────────────

@app.get("/stats")
async def get_stats(x_admin_token: str = Header(None)):
    _require_auth(x_admin_token)
    async with AsyncSessionLocal() as session:
        total_users = (await session.execute(
            select(func.count()).select_from(User)
        )).scalar_one_or_none() or 0

        total_quizzes = (await session.execute(
            select(func.count()).select_from(Quiz).where(Quiz.deleted_at.is_(None))
        )).scalar_one_or_none() or 0

        active_subs = (await session.execute(
            select(func.count()).select_from(Subscription).where(Subscription.status == "active")
        )).scalar_one_or_none() or 0

        total_revenue = (await session.execute(
            select(func.sum(Payment.amount)).where(Payment.status == "completed")
        )).scalar_one_or_none() or 0

    return {
        "total_users": total_users,
        "total_quizzes": total_quizzes,
        "active_subscriptions": active_subs,
        "total_revenue_uzs": total_revenue,
    }


# ─────────────────────────── Foydalanuvchilar ───────────────────────────

@app.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(50, le=200),
    x_admin_token: str = Header(None),
):
    _require_auth(x_admin_token)
    offset = (page - 1) * limit
    async with AsyncSessionLocal() as session:
        total = (await session.execute(
            select(func.count()).select_from(User)
        )).scalar_one_or_none() or 0

        result = await session.execute(
            select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
        )
        users = result.scalars().all()

    return {
        "users": [
            {
                "id": str(u.id),
                "telegram_id": u.telegram_id,
                "username": u.username,
                "first_name": u.first_name,
                "language_code": u.language_code,
                "is_bot_blocked": u.is_bot_blocked,
                "last_active_at": u.last_active_at.isoformat() if u.last_active_at else None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit if total > 0 else 1,
    }


@app.get("/users/{user_id}")
async def get_user(user_id: str, x_admin_token: str = Header(None)):
    _require_auth(x_admin_token)
    import uuid as uuid_mod
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.id == uuid_mod.UUID(user_id))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    return {
        "id": str(user.id),
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "language_code": user.language_code,
        "is_bot_blocked": user.is_bot_blocked,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@app.delete("/users/{user_id}")
async def block_user(user_id: str, x_admin_token: str = Header(None)):
    """Foydalanuvchini bloklash (soft delete emas — is_bot_blocked = True)"""
    _require_auth(x_admin_token)
    import uuid as uuid_mod
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User)
            .where(User.id == uuid_mod.UUID(user_id))
            .values(is_bot_blocked=True)
        )
        await session.commit()
    return {"blocked": True}


# ─────────────────────────── Quizlar ───────────────────────────

@app.get("/quizzes")
async def list_quizzes(
    page: int = Query(1, ge=1),
    limit: int = Query(50, le=200),
    visibility: Optional[str] = Query(None),
    x_admin_token: str = Header(None),
):
    _require_auth(x_admin_token)
    offset = (page - 1) * limit
    async with AsyncSessionLocal() as session:
        stmt = select(Quiz).where(Quiz.deleted_at.is_(None))
        count_stmt = select(func.count()).select_from(Quiz).where(Quiz.deleted_at.is_(None))
        if visibility:
            stmt = stmt.where(Quiz.visibility == visibility)
            count_stmt = count_stmt.where(Quiz.visibility == visibility)

        total = (await session.execute(count_stmt)).scalar_one_or_none() or 0
        result = await session.execute(
            stmt.order_by(Quiz.created_at.desc()).offset(offset).limit(limit)
        )
        quizzes = result.scalars().all()

    return {
        "quizzes": [
            {
                "id": str(q.id),
                "title": q.title,
                "owner_id": str(q.owner_id),
                "total_questions": q.total_questions,
                "play_count": q.play_count,
                "visibility": q.visibility,
                "is_active": q.is_active,
                "created_at": q.created_at.isoformat() if q.created_at else None,
            }
            for q in quizzes
        ],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit if total > 0 else 1,
    }


@app.delete("/quizzes/{quiz_id}")
async def delete_quiz(quiz_id: str, x_admin_token: str = Header(None)):
    """Quizni soft-delete qilish"""
    _require_auth(x_admin_token)
    import uuid as uuid_mod
    from datetime import datetime, timezone
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Quiz)
            .where(Quiz.id == uuid_mod.UUID(quiz_id))
            .values(deleted_at=datetime.now(timezone.utc), is_active=False)
        )
        await session.commit()
    return {"deleted": True}


# ─────────────────────────── Sozlamalar ───────────────────────────

@app.get("/settings")
async def get_settings(x_admin_token: str = Header(None)):
    """Tizim sozlamalarini o'qish"""
    _require_auth(x_admin_token)
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Setting))
        settings = result.scalars().all()
    return {s.key: {"value": s.value, "description": s.description} for s in settings}


class SettingUpdate(BaseModel):
    value: Any
    description: Optional[str] = None


@app.put("/settings/{key}")
async def update_setting(key: str, body: SettingUpdate, x_admin_token: str = Header(None)):
    """Sozlamani yangilash yoki yaratish"""
    _require_auth(x_admin_token)
    from datetime import datetime, timezone
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()

        if setting:
            await session.execute(
                update(Setting)
                .where(Setting.key == key)
                .values(
                    value=body.value,
                    description=body.description or setting.description,
                    updated_at=datetime.now(timezone.utc),
                )
            )
        else:
            session.add(Setting(
                key=key,
                value=body.value,
                description=body.description or "",
            ))
        await session.commit()
    return {"key": key, "updated": True}


# ─────────────────────────── Adminlar ───────────────────────────

@app.get("/admins")
async def list_admins(x_admin_token: str = Header(None)):
    _require_auth(x_admin_token)
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Admin).where(Admin.is_active.is_(True)))
        admins = result.scalars().all()
    return {
        "admins": [
            {
                "id": str(a.id),
                "telegram_id": a.telegram_id,
                "username": a.username,
                "role": a.role,
            }
            for a in admins
        ]
    }


class AdminCreate(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    role: str = "moderator"


@app.post("/admins")
async def create_admin(body: AdminCreate, x_admin_token: str = Header(None)):
    _require_auth(x_admin_token)
    async with AsyncSessionLocal() as session:
        admin = Admin(
            telegram_id=body.telegram_id,
            username=body.username,
            role=body.role,
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
    return {"id": str(admin.id), "telegram_id": admin.telegram_id, "role": admin.role}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("ADMIN_API_PORT", "8004"))
    uvicorn.run(app, host="0.0.0.0", port=port)
