"""
database.py

Configures the async SQLModel engine and provides context-managed async session
for use with FastAPI and background jobs. Supports environment-based configuration.
"""

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./car_repair.db")

# Correct: use the ASYNC engine!
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    future=True,
)


async def init_db() -> None:
    """
    Create all tables (idempotent) using SQLModel metadata.
    Call this on startup for initial migration in simple demos.
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def drop_db() -> None:
    """
    Drop all tables (for test/CI teardown).
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for async session, to be used in FastAPI endpoints.

    Yields:
        AsyncSession: An async SQLModel session.
    """
    async with AsyncSession(engine) as session:
        yield session
