"""Tizim sozlamalari va adminlar boshqaruvi."""
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from deps import require_auth, get_db
from models import Admin, Setting

router = APIRouter(tags=["settings"])


# ── Settings ──────────────────────────────────────────────────────────────

@router.get("/settings", dependencies=[Depends(require_auth)])
async def get_settings(db: AsyncSession = Depends(get_db)):
    settings = (await db.execute(select(Setting))).scalars().all()
    return {s.key: {"value": s.value, "description": s.description} for s in settings}


class SettingUpdate(BaseModel):
    value: Any
    description: Optional[str] = None


@router.put("/settings/{key}", dependencies=[Depends(require_auth)])
async def update_setting(key: str, body: SettingUpdate, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(
        select(Setting).where(Setting.key == key)
    )).scalar_one_or_none()

    if existing:
        await db.execute(
            update(Setting).where(Setting.key == key).values(
                value=body.value,
                description=body.description or existing.description,
                updated_at=datetime.now(timezone.utc),
            )
        )
    else:
        db.add(Setting(key=key, value=body.value, description=body.description or ""))

    await db.commit()
    return {"key": key, "updated": True}


# ── Adminlar ──────────────────────────────────────────────────────────────

@router.get("/admins", dependencies=[Depends(require_auth)])
async def list_admins(db: AsyncSession = Depends(get_db)):
    admins = (await db.execute(
        select(Admin).where(Admin.is_active.is_(True))
    )).scalars().all()
    return {
        "admins": [
            {
                "id": str(a.id),
                "telegram_id": a.telegram_id,
                "username": a.username,
                "role": a.role,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in admins
        ]
    }


class AdminCreate(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    role: str = "moderator"


@router.post("/admins", dependencies=[Depends(require_auth)])
async def create_admin(body: AdminCreate, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(
        select(Admin).where(Admin.telegram_id == body.telegram_id)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Bu telegram_id allaqachon admin")

    admin = Admin(
        telegram_id=body.telegram_id,
        username=body.username,
        role=body.role,
        is_active=True,
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    return {"id": str(admin.id), "telegram_id": admin.telegram_id, "role": admin.role}


@router.delete("/admins/{admin_id}", dependencies=[Depends(require_auth)])
async def remove_admin(admin_id: str, db: AsyncSession = Depends(get_db)):
    import uuid as uuid_mod
    await db.execute(
        update(Admin)
        .where(Admin.id == uuid_mod.UUID(admin_id))
        .values(is_active=False)
    )
    await db.commit()
    return {"removed": True, "admin_id": admin_id}
