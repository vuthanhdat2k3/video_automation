import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text as sa_text

# Force test database URL before any app imports
default_test_db = "postgresql+asyncpg://ai2d:ai2d_pass@localhost:15432/ai2d_flow"
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", default_test_db)

# Also configure AIOHTTP to use port 15432 for tests
import app.config as _cfg  # noqa: E402
_cfg.settings.database_url = os.environ["DATABASE_URL"]

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.services.storage import StorageManager

TEST_DATABASE_URL = settings.database_url

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_async_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db():
    """Create tables for DB-backed tests."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.execute(sa_text("DROP TABLE IF EXISTS jobs CASCADE"))
        await conn.execute(sa_text("DROP TABLE IF EXISTS shots CASCADE"))
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(db) -> AsyncSession:
    """Yield a database session for tests that need it."""
    async with test_async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture
async def client(db) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
