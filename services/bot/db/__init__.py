"""
Async SQLAlchemy engine setup and session factory.

Environment variables:
  DATABASE_URL — asyncpg DSN, e.g.
                 postgresql+asyncpg://user:pass@host/dbname
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .models import Base  # noqa: F401 – re-exported for convenience

DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/quizbot",
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_session() -> AsyncGenerator[AsyncSession, Any]:
    """Dependency that yields an AsyncSession and commits/rolls back on exit."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_tables() -> None:
    """Create all tables that don't exist yet (used on startup)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
