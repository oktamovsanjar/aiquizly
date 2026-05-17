"""Admin API SQLAlchemy modellari — faqat o'qish (admin-api o'z jadvallariga yozadi)."""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class User(Base):
    """users jadvali — bot xizmatiniki, admin faqat o'qiydi."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    language_code = Column(String(10), default="uz")
    is_bot_blocked = Column(Boolean, default=False)
    last_active_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Quiz(Base):
    """quizzes jadvali — ai-engine xizmatiniki, admin faqat o'qiydi."""
    __tablename__ = "quizzes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    quiz_group_id = Column(UUID(as_uuid=True))
    title = Column(String(300), nullable=False)
    description = Column(Text)
    visibility = Column(String(20), default="private")
    source_type = Column(String(20))
    total_questions = Column(Integer, default=0)
    play_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    deleted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Subscription(Base):
    """subscriptions jadvali — subscription xizmatiniki."""
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    plan_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String(20), nullable=False)
    started_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime)
    auto_renew = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Payment(Base):
    """payments jadvali — subscription xizmatiniki."""
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    subscription_id = Column(UUID(as_uuid=True))
    provider = Column(String(20), nullable=False)
    provider_payment_id = Column(String(255))
    amount = Column(Integer, nullable=False)
    currency = Column(String(10), default="UZS")
    status = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Admin(Base):
    """admins jadvali — admin-api xizmatiniki."""
    __tablename__ = "admins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(255))
    role = Column(String(20), default="moderator")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Setting(Base):
    """settings jadvali — admin-api xizmatiniki."""
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(JSONB, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)
