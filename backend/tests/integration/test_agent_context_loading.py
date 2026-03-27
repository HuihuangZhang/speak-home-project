"""Integration tests: agent loads session context from DB on resume."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from shared.models import Session as SessionModel, Message, User
from shared.session_state import SessionStatus

pytestmark = pytest.mark.asyncio


async def test_agent_loads_last_20_messages_on_resume(db_session):
    from agent.tutor import load_session_context

    # Create a user and session
    user = User(email="athlete@example.com", hashed_password="x")
    db_session.add(user)
    await db_session.flush()

    session = SessionModel(user_id=user.id, status=SessionStatus.PAUSED, room_name="session-42")
    db_session.add(session)
    await db_session.flush()

    # Insert 25 messages
    for i in range(25):
        db_session.add(Message(session_id=session.id, role="user" if i % 2 == 0 else "assistant", content=f"message {i}"))
    await db_session.commit()

    context = await load_session_context(db=db_session, session_id=session.id)

    assert len(context["messages"]) == 20
    # Must be the LAST 20 (most recent)
    assert "message 24" in context["messages"][-1]["content"]
    assert "message 5" in context["messages"][0]["content"]


async def test_agent_loads_exercise_plan_on_resume(db_session):
    from agent.tutor import load_session_context

    user = User(email="runner@example.com", hashed_password="x")
    db_session.add(user)
    await db_session.flush()

    plan = {"exercises": ["running", "cycling"], "sets": 3}
    session = SessionModel(
        user_id=user.id,
        status=SessionStatus.PAUSED,
        room_name="session-43",
        exercise_plan=plan,
    )
    db_session.add(session)
    await db_session.commit()

    context = await load_session_context(db=db_session, session_id=session.id)

    assert context["exercise_plan"] == plan


async def test_agent_dispatch_metadata_parsing():
    from agent.tutor import parse_dispatch_metadata

    raw_metadata = {"session_id": "123", "user_id": "456"}
    session_id, user_id = parse_dispatch_metadata(raw_metadata)

    assert session_id == 123
    assert user_id == 456


async def test_agent_dispatch_metadata_missing_key_raises():
    from agent.tutor import parse_dispatch_metadata

    with pytest.raises(KeyError):
        parse_dispatch_metadata({"session_id": "1"})  # missing user_id
