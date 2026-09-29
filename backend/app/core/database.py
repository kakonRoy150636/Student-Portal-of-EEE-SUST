from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

def _engine_kwargs(url: str) -> dict:
    """Pool tuning only makes sense for a driver that has a pool to size.

    SQLite -- which is what a `DATABASE_URL=sqlite+aiosqlite:///...` scratch or
    demo database points at -- uses StaticPool/NullPool internally and raises
    ``TypeError: Invalid argument(s) 'pool_size', 'max_overflow'`` if they are
    passed, so this module could not even be imported. Postgres keeps the lot.
    """

    if url.startswith("sqlite"):
        return {"echo": settings.DB_ECHO}
    return {
        "echo": settings.DB_ECHO,
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }


engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs(settings.DATABASE_URL))

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
