"""
Database Configuration and Session Management
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.infrastructure.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


# Sync engine (for Alembic migrations)
sync_engine = create_engine(
    settings.sqlalchemy_database_url.replace("postgresql+asyncpg", "postgresql"),
    echo=settings.database_echo,
)

# Async engine (for application)
async_engine = create_async_engine(
    settings.sqlalchemy_database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.database_echo,
)

# Session factories
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
