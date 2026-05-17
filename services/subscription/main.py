import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from limits.checker import LimitChecker
from payments.telegram_stars import generate_invoice_payload, verify_payment, decode_payload, PERIOD_DAYS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# --- DB setup ---
engine = create_async_engine(
    DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    pool_size=10,
    max_overflow=5,
    echo=False,
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# --- Redis setup ---
redis_client: Redis = None
limit_checker = LimitChecker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    redis_client = Redis.from_url(REDIS_URL, decode_responses=True)
    logger.info("Subscription xizmati ishga tushdi")
    yield
    await redis_client.aclose()
    await engine.dispose()
    logger.info("Subscription xizmati to'xtatildi")


app = FastAPI(title="Quiz Bot Subscription", lifespan=lifespan)


@app.get("/health")
async def health():
    db_status = "ok"
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    redis_status = "ok"
    try:
        await redis_client.ping()
    except Exception:
        redis_status = "error"

    return {
        "status": "healthy",
        "service": "subscription",
        "version": "1.0.0",
        "checks": {"database": db_status, "redis": redis_status},
    }


@app.get("/limits/check")
async def check_limit(
    user_id: Optional[str] = Query(None, description="UUID formatida user_id"),
    telegram_id: Optional[int] = Query(None, description="Telegram user ID"),
    action: str = Query(..., description="file_upload | quiz_create"),
):
    """
    Bot middleware dan chaqiriladi.
    user_id (UUID) yoki telegram_id orqali chaqirish mumkin.
    """
    resolved_user_id = user_id

    # telegram_id bo'yicha UUID topish
    if not resolved_user_id and telegram_id:
        try:
            from sqlalchemy import text
            async with AsyncSessionLocal() as session:
                row = await session.execute(
                    text("SELECT id FROM users WHERE telegram_id = :tid"),
                    {"tid": telegram_id},
                )
                rec = row.fetchone()
                resolved_user_id = str(rec[0]) if rec else None
        except Exception as e:
            logger.warning("telegram_id → UUID xatosi: %s", e)

    if not resolved_user_id:
        # Foydalanuvchi hali DB da yo'q (yangi) — ruxsat beriladi
        return {"allowed": True, "limit": 3, "used": 0, "plan": "free"}

    async with AsyncSessionLocal() as session:
        try:
            result = await limit_checker.check(
                session=session,
                redis=redis_client,
                user_id=resolved_user_id,
                action=action,
            )
            return result
        except Exception as e:
            logger.error("Limit tekshirish xatosi: %s", e)
            return {"allowed": True, "limit": None, "used": 0, "plan": "free"}


@app.post("/limits/increment")
async def increment_usage(
    user_id: Optional[str] = Query(None),
    telegram_id: Optional[int] = Query(None),
    action: str = Query(...),
):
    """Foydalanish sonini oshiradi (fayl yuklangandan keyin chaqiriladi)"""
    resolved_user_id = user_id
    if not resolved_user_id and telegram_id:
        try:
            from sqlalchemy import text
            async with AsyncSessionLocal() as session:
                row = await session.execute(
                    text("SELECT id FROM users WHERE telegram_id = :tid"),
                    {"tid": telegram_id},
                )
                rec = row.fetchone()
                resolved_user_id = str(rec[0]) if rec else None
        except Exception as e:
            logger.warning("telegram_id → UUID xatosi: %s", e)

    if not resolved_user_id:
        return {"success": True}

    async with AsyncSessionLocal() as session:
        try:
            await limit_checker.increment(
                session=session,
                redis=redis_client,
                user_id=resolved_user_id,
                action=action,
            )
            await session.commit()
            return {"success": True}
        except Exception as e:
            logger.error("Increment xatosi: %s", e)
            raise HTTPException(status_code=500, detail="Increment xatosi")


@app.get("/plans")
async def list_plans():
    """Mavjud tariflar ro'yxati"""
    async with AsyncSessionLocal() as session:
        try:
            from db.queries import get_all_active_plans
            plans = await get_all_active_plans(session)
            return {
                "plans": [
                    {
                        "id": str(p.id),
                        "name": p.name,
                        "price_monthly": p.price_monthly,
                        "price_yearly": p.price_yearly,
                        "max_uploads_per_month": p.max_uploads_per_month,
                        "max_questions_per_file": p.max_questions_per_file,
                        "can_share_group": p.can_share_group,
                        "quiz_retention_days": p.quiz_retention_days,
                    }
                    for p in plans
                ]
            }
        except Exception:
            # DB bo'sh bo'lsa — hardcoded response
            return {
                "plans": [
                    {"name": "free", "price_monthly": 0, "max_uploads_per_month": 3, "max_questions_per_file": 50},
                    {"name": "premium", "price_monthly": 29000, "price_yearly": 249000, "max_uploads_per_month": None},
                    {"name": "business", "price_monthly": None, "max_uploads_per_month": None},
                ]
            }


@app.get("/subscriptions/{user_id}")
async def get_subscription(user_id: str):
    """Foydalanuvchi obunasini olish"""
    async with AsyncSessionLocal() as session:
        from db.queries import get_active_subscription
        import uuid as uuid_mod
        sub = await get_active_subscription(session, uuid_mod.UUID(user_id))
        if not sub:
            return {"plan": "free", "status": "none", "expires_at": None}
        await session.refresh(sub, ["plan"])
        return {
            "plan": sub.plan.name if sub.plan else "free",
            "status": sub.status,
            "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
            "auto_renew": sub.auto_renew,
        }


# --- To'lov endpointlari ---

class StarsInvoiceRequest(BaseModel):
    user_id: str
    plan: str       # premium | business
    period: str     # monthly | yearly


@app.post("/payments/stars/invoice")
async def create_stars_invoice(req: StarsInvoiceRequest):
    """Telegram Stars invoice ma'lumotlarini yaratish"""
    try:
        invoice = generate_invoice_payload(req.user_id, req.plan, req.period)
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class StarsCompleteRequest(BaseModel):
    user_id: str
    provider_payment_id: str
    payload: str    # Telegram tomonidan qaytarilgan opaque payload


@app.post("/payments/stars/complete")
async def complete_stars_payment(req: StarsCompleteRequest):
    """Telegram Stars to'lovni tasdiqlash va obuna yaratish"""
    if not verify_payment(req.provider_payment_id):
        raise HTTPException(status_code=400, detail="To'lov tasdiqlanmadi")

    try:
        payload_data = decode_payload(req.payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    plan_name = payload_data.get("plan")
    period = payload_data.get("period")
    days = PERIOD_DAYS.get(period, 30)

    async with AsyncSessionLocal() as session:
        from db.queries import get_plan, create_subscription, create_payment, complete_payment
        import uuid as uuid_mod

        user_uuid = uuid_mod.UUID(req.user_id)
        plan = await get_plan(session, plan_name)
        if not plan:
            raise HTTPException(status_code=400, detail=f"Plan topilmadi: {plan_name}")

        sub = await create_subscription(session, user_uuid, plan.id, days)
        payment = await create_payment(
            session=session,
            user_id=user_uuid,
            subscription_id=sub.id,
            provider="telegram_stars",
            amount=payload_data.get("stars", 0),
            currency="XTR",
            provider_payment_id=req.provider_payment_id,
        )
        await complete_payment(session, payment.id, req.provider_payment_id)
        await session.commit()

    logger.info("Stars to'lov tasdiqlandi: user=%s plan=%s days=%d", req.user_id, plan_name, days)
    return {"success": True, "plan": plan_name, "days": days}


class ReferralBonusRequest(BaseModel):
    user_id: str
    bonus_days: int = 3


@app.post("/subscriptions/bonus")
async def add_referral_bonus(req: ReferralBonusRequest):
    """Referal uchun bonus kun qo'shish"""
    async with AsyncSessionLocal() as session:
        from db.queries import add_bonus_days
        import uuid as uuid_mod
        await add_bonus_days(session, uuid_mod.UUID(req.user_id), req.bonus_days)
        await session.commit()
    return {"success": True, "bonus_days": req.bonus_days}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SUBSCRIPTION_PORT", "8003"))
    uvicorn.run(app, host="0.0.0.0", port=port)
