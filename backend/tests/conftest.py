import os

# Set test environment variables BEFORE importing any app modules
# (pydantic-settings reads env at import time)
os.environ.setdefault("LIVEKIT_URL", "wss://test.livekit.cloud")
os.environ.setdefault("LIVEKIT_API_URL", "https://livekit-api.example.com")
os.environ.setdefault("LIVEKIT_API_KEY", "test-api-key")
os.environ.setdefault("LIVEKIT_API_SECRET", "test-api-secret-32-chars-minimum!!!")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("DEEPGRAM_API_KEY", "test-deepgram-key")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-32-chars-minimum!")
os.environ.setdefault("JWT_EXPIRE_HOURS", "24")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SESSION_PAUSE_TIMEOUT_MINUTES", "5")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from shared.db import Base, get_db
from api.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Patch AsyncSessionLocal so background tasks (e.g. _run_summary) use the test DB
    import shared.db as shared_db

    original_session_local = shared_db.AsyncSessionLocal
    patched_session_local = async_sessionmaker(engine, expire_on_commit=False)
    shared_db.AsyncSessionLocal = patched_session_local

    import agent.summary as agent_summary
    original_summary_session_local = agent_summary.AsyncSessionLocal
    agent_summary.AsyncSessionLocal = patched_session_local

    yield engine

    shared_db.AsyncSessionLocal = original_session_local
    agent_summary.AsyncSessionLocal = original_summary_session_local
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """FastAPI test client wired to the in-memory DB."""
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def user_payload():
    return {"email": "coach@example.com", "password": "StrongPass123!"}


@pytest_asyncio.fixture
async def auth_headers(client, user_payload):
    """Register + login, return Authorization header."""
    await client.post("/auth/register", json=user_payload)
    resp = await client.post("/auth/login", json=user_payload)
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
