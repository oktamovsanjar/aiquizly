"""Admin API SQLAlchemy modellari."""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class User(Base):
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


class ImportLog(Base):
    __tablename__ = "import_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True))
    quiz_id = Column(UUID(as_uuid=True))
    file_name = Column(String(500))
    file_hash = Column(String(64))
    file_size = Column(Integer)
    file_type = Column(String(20))
    status = Column(String(20), default="pending")
    total_detected = Column(Integer, default=0)
    total_imported = Column(Integer, default=0)
    error_message = Column(Text)
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Subscription(Base):
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
    __tablename__ = "admins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(255))
    role = Column(String(20), default="moderator")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(JSONB, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)


class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(100), unique=True, nullable=False)
    text_uz = Column(Text, nullable=False)
    text_ru = Column(Text)
    text_en = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    template_id = Column(UUID(as_uuid=True))
    custom_text = Column(Text)
    reference_type = Column(String(50))
    status = Column(String(20), default="pending")
    sent_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
