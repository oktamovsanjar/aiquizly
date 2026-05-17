"""
SQLAlchemy async models for bot-owned tables.
Schema matches shared/migrations/001_create_users.sql and 003_create_quiz_tables.sql.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str] = mapped_column(String(10), nullable=False, default="uz")
    is_bot_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    referred_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    quiz_groups: Mapped[list[QuizGroup]] = relationship(
        "QuizGroup", back_populates="owner", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_users_telegram_id", "telegram_id"),
        Index("ix_users_last_active_at", "last_active_at"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} telegram_id={self.telegram_id} username={self.username}>"


class QuizGroup(Base):
    __tablename__ = "quiz_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    subscriber_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quiz_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    owner: Mapped[User] = relationship("User", back_populates="quiz_groups")
    subscribers: Mapped[list[QuizGroupSubscriber]] = relationship(
        "QuizGroupSubscriber", back_populates="quiz_group", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_quiz_groups_owner_id", "owner_id"),
        Index("ix_quiz_groups_slug", "slug"),
    )

    def __repr__(self) -> str:
        return f"<QuizGroup id={self.id} name={self.name}>"


class QuizGroupSubscriber(Base):
    __tablename__ = "quiz_group_subscribers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quiz_groups.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notify: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    subscribed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship("User")
    quiz_group: Mapped[QuizGroup] = relationship("QuizGroup", back_populates="subscribers")

    __table_args__ = (
        UniqueConstraint("quiz_group_id", "user_id", name="idx_qgs_unique"),
        Index("ix_quiz_group_subscribers_user_id", "user_id"),
    )


class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    referrer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    referred_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    bonus_given: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    bonus_days: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("referrer_id", "referred_id", name="idx_referrals_unique"),
        Index("ix_referrals_referrer_id", "referrer_id"),
    )

    def __repr__(self) -> str:
        return f"<Referral referrer={self.referrer_id} referred={self.referred_id}>"


class TelegramGroup(Base):
    __tablename__ = "telegram_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    added_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    voting_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    min_voters: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    voting_timeout: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    who_can_start: Mapped[str] = mapped_column(String(20), nullable=False, default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_telegram_groups_chat_id", "chat_id"),
    )

    def __repr__(self) -> str:
        return f"<TelegramGroup id={self.id} chat_id={self.chat_id} title={self.title}>"
