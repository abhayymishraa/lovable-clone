from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://user:password@localhost/webbuilder"
)

# Creates a connection pool that supports async I/O.
# Production-ready settings for Supabase connection pooler
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True,
    pool_pre_ping=True,  # Test connections before using them
    pool_size=5,  # Number of connections to keep open
    max_overflow=10,  # Additional connections when pool is full
    pool_recycle=3600,  # Recycle connections after 1 hour
    connect_args={
        "statement_cache_size": 0,  # Required for pgbouncer
        "server_settings": {
            "application_name": "lovable-backend",
            "jit": "off"
        }
    }
)


# async_sessionmaker() creates a factory for new async sessions.
# Every time you call AsyncSessionLocal(), you get a new independent database session.
# class_=AsyncSession → ensures it returns async sessions (not sync ones).
# expire_on_commit=False → means objects remain “usable” even after commit.
# If it were True, SQLAlchemy would clear object state after a commit.

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    # Creates a database session.
    async with AsyncSessionLocal() as session:
        try:
            # “Pauses” the function and hands out the session object to whoever called get_db().
            yield session
            # When the route finishes using the session, Python returns control back to get_db() — continuing after the yield line.
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
