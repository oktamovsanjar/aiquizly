"""All DB operations for the ai-engine service."""
import math
import re
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ImportLog, Question, Quiz, QuizSet, QuizTag, Tag


# ---------------------------------------------------------------------------
# ImportLog
# ---------------------------------------------------------------------------

async def create_import_log(
    session: AsyncSession,
    user_id: Optional[str],
    file_name: str,
    file_hash: str,
    file_size: int,
    file_type: str,
) -> ImportLog:
    """Creates a new import_log record with status='processing'."""
    log = ImportLog(
        user_id=uuid.UUID(user_id) if user_id else None,
        file_name=file_name,
        file_hash=file_hash,
        file_size=file_size,
        file_type=file_type,
        status="processing",
    )
    session.add(log)
    await session.flush()
    await session.refresh(log)
    return log


async def update_import_log(
    session: AsyncSession,
    log_id: uuid.UUID,
    status: str,
    quiz_id: Optional[uuid.UUID] = None,
    total_detected: int = 0,
    total_imported: int = 0,
    total_failed: int = 0,
    error_message: Optional[str] = None,
    processing_time_ms: Optional[int] = None,
) -> None:
    """Updates an existing import_log record."""
    values: dict = {
        "status": status,
        "total_detected": total_detected,
        "total_imported": total_imported,
        "total_failed": total_failed,
    }
    if quiz_id is not None:
        values["quiz_id"] = quiz_id
    if error_message is not None:
        values["error_message"] = error_message
    if processing_time_ms is not None:
        values["processing_time_ms"] = processing_time_ms
    if status in ("completed", "failed", "review"):
        values["completed_at"] = datetime.utcnow()

    stmt = update(ImportLog).where(ImportLog.id == log_id).values(**values)
    await session.execute(stmt)


async def check_file_hash(
    session: AsyncSession, file_hash: str
) -> Optional[ImportLog]:
    """Returns an existing ImportLog if the file was already processed successfully."""
    stmt = (
        select(ImportLog)
        .where(ImportLog.file_hash == file_hash)
        .where(ImportLog.status == "completed")
        .order_by(ImportLog.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------

async def create_quiz(
    session: AsyncSession,
    owner_id: str,
    title: str,
    source_type: str,
    quiz_group_id: Optional[str] = None,
) -> Quiz:
    """Creates a new quiz record."""
    quiz = Quiz(
        owner_id=uuid.UUID(owner_id),
        quiz_group_id=uuid.UUID(quiz_group_id) if quiz_group_id else None,
        title=title,
        source_type=source_type,
        visibility="private",
    )
    session.add(quiz)
    await session.flush()
    await session.refresh(quiz)
    return quiz


async def get_quiz(
    session: AsyncSession, quiz_id: str
) -> Optional[Quiz]:
    """Returns a quiz by ID (not soft-deleted)."""
    stmt = (
        select(Quiz)
        .where(Quiz.id == uuid.UUID(quiz_id))
        .where(Quiz.deleted_at.is_(None))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_quizzes(
    session: AsyncSession, user_id: str
) -> List[Quiz]:
    """Returns all non-deleted quizzes for a user."""
    stmt = (
        select(Quiz)
        .where(Quiz.owner_id == uuid.UUID(user_id))
        .where(Quiz.deleted_at.is_(None))
        .order_by(Quiz.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def search_quizzes(
    session: AsyncSession,
    query: Optional[str] = None,
    tag_slug: Optional[str] = None,
    visibility: str = "public",
    limit: int = 20,
    offset: int = 0,
) -> List[Quiz]:
    """Searches quizzes by title text and/or tag slug."""
    stmt = (
        select(Quiz)
        .where(Quiz.deleted_at.is_(None))
        .where(Quiz.is_active.is_(True))
        .where(Quiz.visibility == visibility)
    )
    if query:
        stmt = stmt.where(Quiz.title.ilike(f"%{query}%"))
    if tag_slug:
        stmt = stmt.join(QuizTag, QuizTag.quiz_id == Quiz.id).join(
            Tag, Tag.id == QuizTag.tag_id
        ).where(Tag.slug == tag_slug)
    stmt = stmt.order_by(Quiz.play_count.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------

async def create_questions(
    session: AsyncSession,
    quiz_id: uuid.UUID,
    questions: List[dict],
) -> List[Question]:
    """Batch-inserts questions and updates quiz.total_questions."""
    objs = []
    for idx, q in enumerate(questions):
        correct_index = q.get("correct_index", 0)
        obj = Question(
            quiz_id=quiz_id,
            question_text=q["question"],
            question_type="single",
            options=q["options"],
            correct_indices=[correct_index],
            explanation=q.get("explanation") or None,
            sort_order=idx,
        )
        objs.append(obj)
        session.add(obj)

    await session.flush()

    # Update quiz total_questions count
    stmt = (
        update(Quiz)
        .where(Quiz.id == quiz_id)
        .values(total_questions=len(objs))
    )
    await session.execute(stmt)

    return objs


async def get_quiz_questions(
    session: AsyncSession,
    quiz_id: str,
    offset: int = 0,
    limit: int = 20,
) -> List[Question]:
    """Paginated questions for a quiz."""
    stmt = (
        select(Question)
        .where(Question.quiz_id == uuid.UUID(quiz_id))
        .order_by(Question.sort_order)
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# QuizSets
# ---------------------------------------------------------------------------

async def create_quiz_sets(
    session: AsyncSession,
    quiz_id: uuid.UUID,
    total_questions: int,
    set_size: int = 20,
) -> List[QuizSet]:
    """Auto-generates quiz_sets records (one per set_size questions)."""
    sets = []
    num_sets = math.ceil(total_questions / set_size)
    for i in range(num_sets):
        start = i * set_size
        end = min(start + set_size, total_questions) - 1
        count = end - start + 1
        qs = QuizSet(
            quiz_id=quiz_id,
            set_number=i + 1,
            title=f"Set {i + 1}",
            question_count=count,
            start_index=start,
            end_index=end,
        )
        sets.append(qs)
        session.add(qs)

    await session.flush()
    return sets


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[\s\-]+", "_", slug)
    slug = re.sub(r"[^\w]", "", slug)
    return slug[:100]


async def get_or_create_tags(
    session: AsyncSession, tag_slugs: List[str]
) -> List[Tag]:
    """Returns existing tags or creates missing ones. Increments usage_count."""
    if not tag_slugs:
        return []

    # Normalise slugs
    slugs = [_slugify(s) for s in tag_slugs if s.strip()]
    slugs = list(dict.fromkeys(slugs))  # deduplicate, preserve order

    stmt = select(Tag).where(Tag.slug.in_(slugs))
    result = await session.execute(stmt)
    existing = {t.slug: t for t in result.scalars().all()}

    tags: List[Tag] = []
    for slug in slugs:
        if slug in existing:
            tag = existing[slug]
        else:
            # Derive a display name from slug
            name = slug.replace("_", " ").title()
            tag = Tag(name=name, slug=slug, usage_count=0)
            session.add(tag)
            await session.flush()
        tags.append(tag)

    return tags


async def attach_tags_to_quiz(
    session: AsyncSession,
    quiz_id: uuid.UUID,
    tag_ids: List[uuid.UUID],
) -> None:
    """Creates quiz_tags records and increments tag.usage_count."""
    for tag_id in tag_ids:
        qt = QuizTag(quiz_id=quiz_id, tag_id=tag_id)
        session.add(qt)
        # Increment usage_count
        stmt = (
            update(Tag)
            .where(Tag.id == tag_id)
            .values(usage_count=Tag.usage_count + 1)
        )
        await session.execute(stmt)
    await session.flush()


async def get_trending_tags(
    session: AsyncSession, limit: int = 10
) -> List[Tag]:
    """Returns top N tags by usage_count."""
    stmt = select(Tag).order_by(Tag.usage_count.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())
