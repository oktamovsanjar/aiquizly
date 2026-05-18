"""SQLAlchemy 2.0 async models — ai-engine owned tables"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DECIMAL,
    ForeignKey,
    Integer,
    String,
    Text,
    ARRAY,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default=text("now()")
    )

    quiz_tags: Mapped[List["QuizTag"]] = relationship(back_populates="tag")


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        # FK users.id — DB darajasida, ORM da emas (cross-service table)
    )
    quiz_group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        # FK quiz_groups.id — DB darajasida, ORM da emas (cross-service)
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    visibility: Mapped[str] = mapped_column(
        String(20), default="private", server_default="private"
    )
    source_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    total_questions: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    time_per_question: Mapped[int] = mapped_column(
        Integer, default=30, server_default="30"
    )
    play_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    avg_rating: Mapped[float] = mapped_column(
        DECIMAL(3, 2), default=0, server_default="0"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default=text("now()"), onupdate=datetime.utcnow
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    questions: Mapped[List["Question"]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan"
    )
    quiz_sets: Mapped[List["QuizSet"]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan"
    )
    quiz_tags: Mapped[List["QuizTag"]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan"
    )
    import_logs: Mapped[List["ImportLog"]] = relationship(back_populates="quiz")


class QuizTag(Base):
    __tablename__ = "quiz_tags"

    quiz_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )

    quiz: Mapped["Quiz"] = relationship(back_populates="quiz_tags")
    tag: Mapped["Tag"] = relationship(back_populates="quiz_tags")


class QuizSet(Base):
    __tablename__ = "quiz_sets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False
    )
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    start_index: Mapped[int] = mapped_column(Integer, nullable=False)
    end_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default=text("now()")
    )

    quiz: Mapped["Quiz"] = relationship(back_populates="quiz_sets")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(
        String(20), default="single", server_default="single"
    )
    options: Mapped[list] = mapped_column(JSONB, nullable=False)
    correct_indices: Mapped[list] = mapped_column(ARRAY(Integer), nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default=text("now()")
    )

    quiz: Mapped["Quiz"] = relationship(back_populates="questions")


class ImportLog(Base):
    __tablename__ = "import_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        # FK users.id — DB darajasida, ORM da emas (cross-service table)
    )
    quiz_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quizzes.id"), nullable=True
    )
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    total_detected: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_imported: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_failed: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default=text("now()")
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    quiz: Mapped[Optional["Quiz"]] = relationship(back_populates="import_logs")
