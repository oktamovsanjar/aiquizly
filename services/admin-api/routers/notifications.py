"""Bildirishnomalar va broadcast."""
import json
import logging
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from deps import require_auth, get_db
from models import Notification, NotificationTemplate, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["notifications"])

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/2")
NOTIFICATION_QUEUE = "notification:queue"


async def _push_to_redis(payload: dict) -> None:
    """Redis notification queue ga xabar qo'shadi."""
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(REDIS_URL, decode_responses=True)
        await client.rpush(NOTIFICATION_QUEUE, json.dumps(payload))
        await client.aclose()
    except Exception as exc:
        logger.error("Redis push xatosi: %s", exc)
        raise HTTPException(status_code=503, detail=f"Redis ulanmadi: {exc}")


# ── Notification templates ──────────────────────────────────────────────────

@router.get("/templates", dependencies=[Depends(require_auth)])
async def list_templates(db: AsyncSession = Depends(get_db)):
    templates = (await db.execute(select(NotificationTemplate))).scalars().all()
    return {
        "templates": [
            {
                "id": str(t.id),
                "slug": t.slug,
                "text_uz": t.text_uz,
                "text_ru": t.text_ru,
                "text_en": t.text_en,
                "is_active": t.is_active,
            }
            for t in templates
        ]
    }


class TemplateUpdate(BaseModel):
    text_uz: Optional[str] = None
    text_ru: Optional[str] = None
    text_en: Optional[str] = None
    is_active: Optional[bool] = None


@router.patch("/templates/{slug}", dependencies=[Depends(require_auth)])
async def update_template(slug: str, body: TemplateUpdate, db: AsyncSession = Depends(get_db)):
    tmpl = (await db.execute(
        select(NotificationTemplate).where(NotificationTemplate.slug == slug)
    )).scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Shablon topilmadi")

    values = body.model_dump(exclude_none=True)
    if values:
        await db.execute(
            update(NotificationTemplate).where(NotificationTemplate.slug == slug).values(**values)
        )
        await db.commit()
    return {"slug": slug, "updated": True}


# ── Broadcast ──────────────────────────────────────────────────────────────

class BroadcastRequest(BaseModel):
    text: str
    user_ids: Optional[List[int]] = None   # telegram_id lar; None = hammaga
    parse_mode: str = "HTML"
    language_code: Optional[str] = None    # faqat shu tildagi userlarga


@router.post("/broadcast", dependencies=[Depends(require_auth)])
async def broadcast(body: BroadcastRequest, db: AsyncSession = Depends(get_db)):
    """
    Tanlangan yoki barcha foydalanuvchilarga xabar yuborish.
    Xabarlar Redis queue ga yoziladi — notifier servisi yuboradi.
    """
    if body.user_ids:
        stmt = select(User.telegram_id).where(
            User.telegram_id.in_(body.user_ids),
            User.is_bot_blocked.is_(False),
        )
    else:
        stmt = select(User.telegram_id).where(User.is_bot_blocked.is_(False))
        if body.language_code:
            stmt = stmt.where(User.language_code == body.language_code)

    tg_ids = (await db.execute(stmt)).scalars().all()
    if not tg_ids:
        return {"queued": 0, "message": "Muvofiq foydalanuvchi topilmadi"}

    for tg_id in tg_ids:
        await _push_to_redis({
            "user_telegram_id": tg_id,
            "text": body.text,
            "parse_mode": body.parse_mode,
        })

    logger.info("Broadcast: %d ta foydalanuvchiga yuborildi", len(tg_ids))
    return {"queued": len(tg_ids)}


# ── Notification tarixi ────────────────────────────────────────────────────

@router.get("", dependencies=[Depends(require_auth)])
async def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(50, le=200),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit
    stmt = select(Notification)
    count_stmt = select(func.count()).select_from(Notification)

    if status:
        stmt = stmt.where(Notification.status == status)
        count_stmt = count_stmt.where(Notification.status == status)

    total = (await db.execute(count_stmt)).scalar() or 0
    notifs = (await db.execute(
        stmt.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
    )).scalars().all()

    return {
        "notifications": [
            {
                "id": str(n.id),
                "user_id": str(n.user_id),
                "custom_text": n.custom_text,
                "status": n.status,
                "sent_at": n.sent_at.isoformat() if n.sent_at else None,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifs
        ],
        "total": total,
        "page": page,
        "pages": max(1, (total + limit - 1) // limit),
    }
