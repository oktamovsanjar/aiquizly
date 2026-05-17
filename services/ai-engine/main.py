import logging
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config import settings
from tasks.process_file import process_file_task

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)

# --- DB setup ---
def _async_url(url: str) -> str:
    url = url.replace("postgresql+asyncpg://", "postgresql+asyncpg://")  # no-op if already correct
    url = url.replace("postgresql://", "postgresql+asyncpg://")
    url = url.replace("postgres://", "postgresql+asyncpg://")
    return url


engine = create_async_engine(
    _async_url(settings.database_url),
    pool_size=10,
    max_overflow=5,
    echo=False,
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AI Engine ishga tushdi")
    yield
    await engine.dispose()
    logger.info("AI Engine to'xtatildi")


app = FastAPI(title="Quiz Bot AI Engine", lifespan=lifespan)


class ProcessRequest(BaseModel):
    file_url: str
    file_name: str
    file_size: int
    user_id: str
    quiz_group_id: Optional[str] = None
    tags: Optional[List[str]] = None


@app.get("/health")
async def health():
    # Redis va DB holatini tekshirish
    db_status = "ok"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception:
        db_status = "error"

    return {
        "status": "healthy",
        "service": "ai-engine",
        "version": "1.0.0",
        "checks": {
            "database": db_status,
            "openai": "configured" if settings.openai_api_key else "missing",
        },
    }


@app.post("/process")
async def process_file(req: ProcessRequest):
    """Faylni AI pipeline orqali qayta ishlash (async, Celery task)"""
    import hashlib
    import httpx

    if req.file_size > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Fayl hajmi katta (max 10MB)")

    # Faylni yuklab olish
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(req.file_url)
            resp.raise_for_status()
            file_content = resp.content
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Fayl yuklab olinmadi: {e}")

    file_hash = hashlib.sha256(file_content).hexdigest()

    # Dublikat tekshirish
    async with AsyncSessionLocal() as session:
        from db.queries import check_file_hash
        existing = await check_file_hash(session, file_hash)
        if existing:
            return {
                "task_id": None,
                "status": "already_processed",
                "quiz_id": str(existing.quiz_id) if existing.quiz_id else None,
            }

        # user_id ni telegram_id dan UUID ga resolve qilish
        import uuid as _uuid
        import sqlalchemy as _sa
        resolved_user_id = req.user_id
        # Agar telegram_id raqam bo'lsa (UUID emas) — users jadvalidan UUID topamiz
        try:
            _uuid.UUID(req.user_id)
        except (ValueError, AttributeError):
            try:
                tg_int = int(req.user_id)
                row = await session.execute(
                    _sa.text("SELECT id FROM users WHERE telegram_id = :tid"),
                    {"tid": tg_int},
                )
                row_one = row.fetchone()
                if row_one:
                    resolved_user_id = str(row_one[0])
                else:
                    resolved_user_id = None
            except Exception:
                resolved_user_id = None

        # Import log yaratish
        from db.queries import create_import_log
        import os
        file_ext = os.path.splitext(req.file_name)[1].lstrip(".")
        import_log = await create_import_log(
            session=session,
            user_id=resolved_user_id,
            file_name=req.file_name,
            file_hash=file_hash,
            file_size=req.file_size,
            file_type=file_ext,
        )
        await session.commit()
        log_id = str(import_log.id)

    # Celery task ga yuborish — resolved UUID ni yuborish (telegram_id emas)
    task = process_file_task.delay(
        file_content_hex=file_content.hex(),
        file_name=req.file_name,
        user_id=resolved_user_id,  # UUID string yoki None
        import_log_id=log_id,
        quiz_group_id=req.quiz_group_id,
        tags=req.tags or [],
    )

    return {"task_id": task.id, "status": "processing", "import_log_id": log_id}


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Celery task holatini so'rash"""
    from celery.result import AsyncResult
    from tasks.process_file import celery_app

    result = AsyncResult(task_id, app=celery_app)
    if result.state == "PENDING":
        return {"status": "processing"}
    elif result.state == "SUCCESS":
        return {"status": "completed", "result": result.result}
    elif result.state == "FAILURE":
        return {"status": "failed", "error": str(result.result)}
    return {"status": result.state.lower()}


@app.get("/quizzes")
async def list_quizzes(
    user_id: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    visibility: str = Query("public"),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
):
    """Quiz qidirish va ro'yxat olish"""
    async with AsyncSessionLocal() as session:
        from db.queries import get_user_quizzes, search_quizzes
        if user_id:
            quizzes = await get_user_quizzes(session, user_id)
        else:
            quizzes = await search_quizzes(
                session, query=q, tag_slug=tag,
                visibility=visibility, limit=limit, offset=offset,
            )
        return {
            "quizzes": [
                {
                    "id": str(quiz.id),
                    "title": quiz.title,
                    "total_questions": quiz.total_questions,
                    "play_count": quiz.play_count,
                    "visibility": quiz.visibility,
                    "created_at": quiz.created_at.isoformat() if quiz.created_at else None,
                }
                for quiz in quizzes
            ]
        }


@app.get("/quizzes/{quiz_id}")
async def get_quiz(quiz_id: str):
    """Quiz ma'lumotlarini olish"""
    async with AsyncSessionLocal() as session:
        from db.queries import get_quiz as _get_quiz
        quiz = await _get_quiz(session, quiz_id)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz topilmadi")
        return {
            "id": str(quiz.id),
            "title": quiz.title,
            "description": quiz.description,
            "total_questions": quiz.total_questions,
            "time_per_question": quiz.time_per_question,
            "play_count": quiz.play_count,
            "visibility": quiz.visibility,
            "source_type": quiz.source_type,
            "expires_at": quiz.expires_at.isoformat() if quiz.expires_at else None,
            "created_at": quiz.created_at.isoformat() if quiz.created_at else None,
        }


@app.get("/quizzes/{quiz_id}/questions")
async def get_quiz_questions(
    quiz_id: str,
    offset: int = Query(0),
    limit: int = Query(20, le=100),
):
    """Quiz savollarini olish (paginatsiya bilan)"""
    async with AsyncSessionLocal() as session:
        from db.queries import get_quiz_questions as _get_questions
        questions = await _get_questions(session, quiz_id, offset=offset, limit=limit)
        return {
            "quiz_id": quiz_id,
            "questions": [
                {
                    "id": str(q.id),
                    "question_text": q.question_text,
                    "options": q.options,
                    "correct_indices": q.correct_indices,
                    "explanation": q.explanation,
                    "sort_order": q.sort_order,
                }
                for q in questions
            ],
            "offset": offset,
            "limit": limit,
        }


@app.get("/tags/trending")
async def get_trending_tags(limit: int = Query(10, le=50)):
    """Trend teglarni olish"""
    async with AsyncSessionLocal() as session:
        from db.queries import get_trending_tags
        tags = await get_trending_tags(session, limit=limit)
        return {
            "tags": [
                {"id": str(t.id), "name": t.name, "slug": t.slug, "usage_count": t.usage_count}
                for t in tags
            ]
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.ai_engine_port)
