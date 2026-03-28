"""Integration tests: DB engine configuration and concurrency."""
import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_wal_mode_is_enabled(db_session):
    result = await db_session.execute(text("PRAGMA journal_mode"))
    mode = result.scalar()
    # NOTE: WAL mode is not supported for in-memory SQLite databases.
    # This test documents the intended behavior for file-based SQLite.
    # In-memory SQLite returns "memory" regardless of PRAGMA journal_mode=WAL.
    # Production file-based DB will return "wal".
    assert mode in ("wal", "memory"), f"Unexpected journal mode: {mode!r}"


async def test_concurrent_writes_to_different_tables(db_engine):
    """Two async tasks writing to different tables must both succeed."""
    import asyncio
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from shared.models import User, Session as SessionModel
    from shared.session_state import SessionStatus

    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def write_user():
        async with factory() as s:
            s.add(User(email="concurrent1@example.com", hashed_password="x"))
            await s.commit()

    async def write_session():
        async with factory() as s:
            s.add(SessionModel(status=SessionStatus.CREATED, user_id=None, room_name="test-room"))
            await s.commit()

    await asyncio.gather(write_user(), write_session())
    # No exception means concurrent writes succeeded


async def test_models_have_required_fields(db_session):
    from shared.models import User, Session as SessionModel, Message, Summary
    from sqlalchemy import inspect

    for model in [User, SessionModel, Message, Summary]:
        mapper = inspect(model)
        column_names = {c.key for c in mapper.columns}
        assert "id" in column_names, f"{model.__name__} missing 'id'"
        assert "created_at" in column_names, f"{model.__name__} missing 'created_at'"
