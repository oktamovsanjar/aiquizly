"""Celery task — to'liq AI pipeline"""

import asyncio
import hashlib
import logging
import time
from typing import Any, Dict, List, Optional

from celery import Celery
from config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "ai_engine",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.task_track_started = True

# ── DB engine singleton — worker process da bir marta yaratiladi ──────────────
# har task uchun yangi engine/pool emas, bitta engine qayta ishlatiladi.
_db_engine = None
_AsyncSessionLocal = None


def _get_session_factory():
    """Worker process da birinchi chaqiriqda engine yaratadi, keyin qayta ishlatadi."""
    global _db_engine, _AsyncSessionLocal
    if _db_engine is None:
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker

        db_url = settings.database_url
        if "postgresql://" in db_url and "asyncpg" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://")

        _db_engine = create_async_engine(
            db_url, pool_size=5, max_overflow=2, echo=False
        )
        _AsyncSessionLocal = sessionmaker(
            _db_engine, class_=AsyncSession, expire_on_commit=False
        )
        logger.info("DB engine yaratildi (worker singleton)")
    return _AsyncSessionLocal


@celery_app.task(bind=True, max_retries=3, name="process_file")
def process_file_task(
    self,
    file_url: str,
    file_name: str,
    user_id: str,
    import_log_id: Optional[str] = None,
    quiz_group_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    To'liq AI pipeline Celery task sifatida.
    file_url — faylni yuklab olish uchun URL (Telegram yoki boshqa).
    Katta faylni Redis broker orqali o'tkazish o'rniga URL yuboriladi.
    """
    try:
        return asyncio.run(
            _process_file_async(
                file_url=file_url,
                file_name=file_name,
                user_id=user_id,
                import_log_id=import_log_id,
                quiz_group_id=quiz_group_id,
                tags=tags or [],
            )
        )
    except Exception as exc:
        logger.error("process_file_task xatosi: %s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=10)


def _chunk_text(text: str, chunk_size: int = 3000, overlap: int = 200) -> list:
    """Matnni teng bo'laklarga bo'ladi. AI har bir bo'lakdan savollarni o'zi ajratadi."""
    from dataclasses import dataclass, field

    @dataclass
    class _Block:
        question: str = ""
        options: list = field(default_factory=list)
        raw_text: str = ""

    chunks = []
    i = 0
    while i < len(text):
        chunk = text[i : i + chunk_size]
        chunks.append(_Block(raw_text=chunk))
        i += chunk_size - overlap
    return chunks


async def _process_file_async(
    file_url: str,
    file_name: str,
    user_id: str,
    import_log_id: Optional[str],
    quiz_group_id: Optional[str],
    tags: List[str],
) -> Dict[str, Any]:
    import httpx
    from parsers import detect_format, parse_word, parse_pdf, parse_excel, parse_text
    from ai import AIStructurer, validate_questions

    start_time = time.time()
    logger.info("Fayl qayta ishlash boshlandi: %s, user: %s", file_name, user_id)

    # Faylni yuklab olish (URL dan — Telegram yoki boshqa manba)
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(file_url)
        resp.raise_for_status()
        file_content = resp.content

    file_hash = hashlib.sha256(file_content).hexdigest()

    # Worker singleton DB session factory
    AsyncSessionLocal = _get_session_factory()

    # Stage 1: Format aniqlash
    file_format = detect_format(file_name)

    # Stage 2: Matn chiqarish
    if file_format == "word":
        raw_text = parse_word(file_content)
    elif file_format == "pdf":
        raw_text = parse_pdf(file_content)
    elif file_format == "excel":
        questions = parse_excel(file_content)
        questions, stats = validate_questions(questions)
        result = _build_result(questions, file_name, file_hash, stats)
        await _save_to_db(
            AsyncSessionLocal,
            result,
            user_id,
            file_name,
            file_hash,
            import_log_id,
            quiz_group_id,
            tags,
            start_time,
        )
        return result
    elif file_format == "text":
        raw_text = parse_text(file_content)
    else:
        raise ValueError(f"Qo'llab-quvvatlanmaydigan format: {file_format}")

    if not raw_text or not raw_text.strip():
        result = {"total_questions": 0, "total_sets": 0, "questions": []}
        await _save_to_db(
            AsyncSessionLocal,
            result,
            user_id,
            file_name,
            file_hash,
            import_log_id,
            quiz_group_id,
            tags,
            start_time,
        )
        return result

    # Stage 3: Matnni bo'laklarga bo'lish va parallel AI strukturlash
    blocks = _chunk_text(raw_text)
    structurer = AIStructurer()
    questions, stats = await structurer.structure_blocks(blocks)

    result = _build_result(questions, file_name, file_hash, stats)
    await _save_to_db(
        AsyncSessionLocal,
        result,
        user_id,
        file_name,
        file_hash,
        import_log_id,
        quiz_group_id,
        tags,
        start_time,
    )
    return result


async def _save_to_db(
    AsyncSessionLocal,
    result: Dict[str, Any],
    user_id: str,
    file_name: str,
    file_hash: str,
    import_log_id: Optional[str],
    quiz_group_id: Optional[str],
    tags: List[str],
    start_time: float,
) -> None:
    """Natijani DB ga saqlash"""
    from db.queries import (
        create_quiz,
        create_questions,
        create_quiz_sets,
        get_or_create_tags,
        attach_tags_to_quiz,
        update_import_log,
    )
    import os

    processing_time_ms = int((time.time() - start_time) * 1000)
    questions = result.get("questions", [])
    total = len(questions)

    async with AsyncSessionLocal() as session:
        try:
            # Quiz yaratish — user_id UUID bo'lishi shart
            # Agar None bo'lsa, users jadvalidan telegram_id orqali topamiz
            resolved_owner = user_id
            if not resolved_owner:
                raise ValueError("user_id (UUID) topilmadi — quiz saqlanmadi")

            title = os.path.splitext(file_name)[0]
            quiz = await create_quiz(
                session=session,
                owner_id=resolved_owner,
                title=title,
                source_type="upload",
                quiz_group_id=quiz_group_id,
            )

            # Savollarni yozish
            if questions:
                await create_questions(session, quiz.id, questions)
                await create_quiz_sets(
                    session, quiz.id, total, settings.default_set_size
                )

            # Teglar
            if tags:
                tag_objs = await get_or_create_tags(session, tags)
                await attach_tags_to_quiz(session, quiz.id, [t.id for t in tag_objs])

            # Import log yangilash
            if import_log_id:
                await update_import_log(
                    session=session,
                    log_id=__import__("uuid").UUID(import_log_id),
                    status="completed",
                    quiz_id=quiz.id,
                    total_detected=total,
                    total_imported=total,
                    processing_time_ms=processing_time_ms,
                )

            await session.commit()
            result["quiz_id"] = str(quiz.id)
            logger.info("Quiz DB ga saqlandi: %s, savollar: %d", quiz.id, total)

        except Exception as e:
            await session.rollback()
            logger.error("DB saqlash xatosi: %s", e, exc_info=True)
            if import_log_id:
                try:
                    await update_import_log(
                        session=session,
                        log_id=__import__("uuid").UUID(import_log_id),
                        status="failed",
                        error_message=str(e),
                        processing_time_ms=processing_time_ms,
                    )
                    await session.commit()
                except Exception:
                    pass


def _build_result(
    questions: list, file_name: str, file_hash: str, stats: dict = None
) -> Dict[str, Any]:
    total = len(questions)
    set_size = settings.default_set_size
    total_sets = (total + set_size - 1) // set_size if total > 0 else 0

    return {
        "total_questions": total,
        "total_sets": total_sets,
        "file_hash": file_hash,
        "questions": questions,
        "warnings": stats or {},
    }
