"""Database persistence foundation using SQLAlchemy 2.0 Async."""

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from finsignal.core.config import Settings


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base for all FinSignal persistent models."""

    pass


def create_db_resources(
    settings: Settings,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Factory creating an AsyncEngine and async_sessionmaker bound to specific settings.

    Avoids global import-time engines and allows clean test database isolation.
    """
    engine = create_async_engine(
        settings.async_database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    session_maker = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    return engine, session_maker


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an AsyncSession from the app-bound session maker.

    Ensures session rollback on unhandled exceptions and deterministic cleanup.
    """
    session_maker: async_sessionmaker[AsyncSession] = request.app.state.session_maker
    async with session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def ping_database(engine: AsyncEngine) -> bool:
    """Execute a lightweight SELECT 1 to verify database connectivity.

    Returns True if the database is reachable, False otherwise.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
