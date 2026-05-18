"""Quiz boshqaruvi."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from deps import require_auth, get_db
from models import Quiz, ImportLog

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


def _quiz_dict(q: Quiz) -> dict:
    return {
        "id": str(q.id),
        "title": q.title,
        "owner_id": str(q.owner_id),
        "total_questions": q.total_questions,
        "play_count": q.play_count,
        "visibility": q.visibility,
        "source_type": q.source_type,
        "is_active": q.is_active,
        "created_at": q.created_at.isoformat() if q.created_at else None,
    }


@router.get("", dependencies=[Depends(require_auth)])
async def list_quizzes(
    page: int = Query(1, ge=1),
    limit: int = Query(50, le=200),
    visibility: Optional[str] = Query(None, pattern="^(public|private)$"),
    source_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit
    stmt = select(Quiz).where(Quiz.deleted_at.is_(None))
    count_stmt = select(func.count()).select_from(Quiz).where(Quiz.deleted_at.is_(None))

    if visibility:
        stmt = stmt.where(Quiz.visibility == visibility)
        count_stmt = count_stmt.where(Quiz.visibility == visibility)
    if source_type:
        stmt = stmt.where(Quiz.source_type == source_type)
        count_stmt = count_stmt.where(Quiz.source_type == source_type)

    total = (await db.execute(count_stmt)).scalar() or 0
    quizzes = (await db.execute(
        stmt.order_by(Quiz.created_at.desc()).offset(offset).limit(limit)
    )).scalars().all()

    return {
        "quizzes": [_quiz_dict(q) for q in quizzes],
        "total": total,
        "page": page,
        "pages": max(1, (total + limit - 1) // limit),
    }


@router.delete("/{quiz_id}", dependencies=[Depends(require_auth)])
async def delete_quiz(quiz_id: str, db: AsyncSession = Depends(get_db)):
    import uuid as uuid_mod
    await db.execute(
        update(Quiz)
        .where(Quiz.id == uuid_mod.UUID(quiz_id))
        .values(deleted_at=datetime.now(timezone.utc), is_active=False)
    )
    await db.commit()
    return {"deleted": True, "quiz_id": quiz_id}


@router.patch("/{quiz_id}/restore", dependencies=[Depends(require_auth)])
async def restore_quiz(quiz_id: str, db: AsyncSession = Depends(get_db)):
    import uuid as uuid_mod
    await db.execute(
        update(Quiz)
        .where(Quiz.id == uuid_mod.UUID(quiz_id))
        .values(deleted_at=None, is_active=True)
    )
    await db.commit()
    return {"restored": True, "quiz_id": quiz_id}


@router.patch("/{quiz_id}/visibility", dependencies=[Depends(require_auth)])
async def set_visibility(
    quiz_id: str,
    visibility: str = Query(..., pattern="^(public|private)$"),
    db: AsyncSession = Depends(get_db),
):
    import uuid as uuid_mod
    await db.execute(
        update(Quiz)
        .where(Quiz.id == uuid_mod.UUID(quiz_id))
        .values(visibility=visibility, updated_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"quiz_id": quiz_id, "visibility": visibility}


@router.get("/import-logs", dependencies=[Depends(require_auth)])
async def list_import_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, le=200),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """AI fayl qayta ishlash tarixi."""
    offset = (page - 1) * limit
    stmt = select(ImportLog)
    count_stmt = select(func.count()).select_from(ImportLog)

    if status:
        stmt = stmt.where(ImportLog.status == status)
        count_stmt = count_stmt.where(ImportLog.status == status)

    total = (await db.execute(count_stmt)).scalar() or 0
    logs = (await db.execute(
        stmt.order_by(ImportLog.created_at.desc()).offset(offset).limit(limit)
    )).scalars().all()

    return {
        "logs": [
            {
                "id": str(l.id),
                "user_id": str(l.user_id) if l.user_id else None,
                "quiz_id": str(l.quiz_id) if l.quiz_id else None,
                "file_name": l.file_name,
                "file_type": l.file_type,
                "file_size": l.file_size,
                "status": l.status,
                "total_detected": l.total_detected,
                "total_imported": l.total_imported,
                "error_message": l.error_message,
                "processing_time_ms": l.processing_time_ms,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ],
        "total": total,
        "page": page,
        "pages": max(1, (total + limit - 1) // limit),
    }
