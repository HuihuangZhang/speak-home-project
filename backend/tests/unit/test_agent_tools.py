"""Tests for LLM tool functions (save_exercise_plan, log_session_note, get_user_fitness_history)."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from agent.tools import save_exercise_plan, log_session_note, get_user_fitness_history


@pytest.mark.asyncio
async def test_save_exercise_plan_writes_to_db():
    mock_db = AsyncMock()
    mock_session_obj = MagicMock(exercise_plan=None)
    mock_db.get.return_value = mock_session_obj

    await save_exercise_plan(
        db=mock_db,
        session_id=1,
        plan={"exercises": ["squats", "lunges"], "sets": 3, "reps": 12},
    )

    assert mock_session_obj.exercise_plan == {"exercises": ["squats", "lunges"], "sets": 3, "reps": 12}
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_log_session_note_creates_message_record():
    mock_db = AsyncMock()

    await log_session_note(db=mock_db, session_id=1, role="assistant", content="User prefers low-impact exercises.")

    mock_db.add.assert_called_once()
    added_obj = mock_db.add.call_args[0][0]
    assert added_obj.session_id == 1
    assert added_obj.role == "assistant"
    assert "low-impact" in added_obj.content
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_user_fitness_history_returns_last_n_messages():
    mock_db = AsyncMock()
    fake_messages = [MagicMock(role="user", content=f"msg {i}") for i in range(25)]
    # Simulate DB returning last 20
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = fake_messages[-20:]
    mock_db.execute.return_value = mock_result

    history = await get_user_fitness_history(db=mock_db, user_id=7, limit=20)

    assert len(history) == 20
    # Verify execute was called and the query filters by user_id=7
    assert mock_db.execute.called
    query = mock_db.execute.call_args[0][0]
    from sqlalchemy.dialects import sqlite
    query_str = str(query.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}))
    assert "7" in query_str


@pytest.mark.asyncio
async def test_save_exercise_plan_raises_if_session_not_found():
    mock_db = AsyncMock()
    mock_db.get.return_value = None

    with pytest.raises(ValueError, match="Session .* not found"):
        await save_exercise_plan(db=mock_db, session_id=999, plan={})
