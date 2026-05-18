"""Shared dependencies — auth, DB session."""
import os

from fastapi import Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "admin-secret-change-me")

DATABASE_URL = os.getenv("DATABASE_URL", "")
_db_url = DATABASE_URL
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif "postgresql://" in _db_url and "asyncpg" not in _db_url:
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(_db_url, pool_size=5, max_overflow=2, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def require_auth(x_admin_token: str = Header(None)) -> None:
    if not x_admin_token or x_admin_token != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Admin token xato yoki yo'q")


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
