"""DB engine setup — SQLAlchemy 2.0 async with asyncpg"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import settings

# asyncpg driver: postgresql+asyncpg://...
_db_url = settings.database_url
if _db_url.startswith("postgresql://") or _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    _db_url = _db_url.replace("postgres://", "postgresql+asyncpg://", 1)

async_engine = create_async_engine(
    _db_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
