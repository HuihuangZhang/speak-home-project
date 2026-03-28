"""Tests for post-session summary generation."""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select, delete

from agent.summary import generate_summary, build_summary_prompt
from shared.db import AsyncSessionLocal
from shared.models import Summary


class TestBuildSummaryPrompt:
    def test_prompt_includes_all_messages(self):
        messages = [
            {"role": "user", "content": "I want to build endurance"},
            {"role": "assistant", "content": "Let's start with a 20-minute run"},
        ]
        prompt = build_summary_prompt(messages)
        assert "endurance" in prompt
        assert "20-minute run" in prompt

    def test_prompt_requests_structured_output(self):
        prompt = build_summary_prompt([])
        # Must instruct the model to return exercises, notes, and recommendations
        assert "exercises" in prompt.lower()
        assert "recommendation" in prompt.lower()

    def test_empty_messages_produces_valid_prompt(self):
        prompt = build_summary_prompt([])
        assert isinstance(prompt, str)
        assert len(prompt) > 0


def _make_mock_db(messages=None, openai_response_content=None):
    """Build a mock AsyncSession that generate_summary can use as a context manager."""
    mock_db = AsyncMock()
    mock_messages_result = MagicMock()
    mock_messages_result.scalars.return_value.all.return_value = messages or []
    mock_db.execute.return_value = mock_messages_result

    # Support `async with AsyncSessionLocal() as db:`
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    return mock_ctx, mock_db


@pytest.mark.asyncio
async def test_generate_summary_writes_done_status():
    mock_ctx, mock_db = _make_mock_db(
        messages=[
            MagicMock(role="user", content="I want to lose weight"),
            MagicMock(role="assistant", content="Here is your plan"),
        ]
    )

    openai_response = MagicMock()
    openai_response.choices[0].message.content = (
        '{"exercises": ["running"], "coaching_notes": ["good pace"], "next_recommendations": ["add strength"]}'
    )

    with patch("agent.summary.AsyncSessionLocal", return_value=mock_ctx), \
         patch("agent.summary.openai_client.chat.completions.create", return_value=openai_response):
        await generate_summary(session_id=1)

    mock_db.add.assert_called_once()
    summary_obj = mock_db.add.call_args[0][0]
    assert summary_obj.status == "done"
    assert summary_obj.session_id == 1


@pytest.mark.asyncio
async def test_generate_summary_real_db_session_32():
    """Integration test: reads real transcript for session 32 from SQLite, mocks only OpenAI.

    The conftest wires AsyncSessionLocal to an in-memory DB, so this test creates its
    own engine pointing at the actual speakhome.db file on disk and patches the module.
    """
    from pathlib import Path
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    db_path = Path(__file__).parent.parent.parent / "speakhome.db"
    real_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    RealSessionLocal = async_sessionmaker(real_engine, expire_on_commit=False)

    # Remove any pre-existing summary for session 32 so the INSERT succeeds
    async with RealSessionLocal() as db:
        await db.execute(delete(Summary).where(Summary.session_id == 32))
        await db.commit()

    mock_openai_response = MagicMock()
    mock_openai_response.choices[0].message.content = json.dumps({
        "exercises": ["squat", "deadlift"],
        "coaching_notes": ["good form on squat", "keep back straight"],
        "next_recommendations": ["add hip mobility", "increase deadlift weight"],
    })

    with patch("agent.summary.AsyncSessionLocal", RealSessionLocal), \
         patch("agent.summary.openai_client.chat.completions.create", return_value=mock_openai_response):
        await generate_summary(session_id=32)

    async with RealSessionLocal() as db:
        result = await db.execute(
            select(Summary)
            .where(Summary.session_id == 32)
            .order_by(Summary.generated_at.desc())
        )
        summary = result.scalars().first()

        await db.execute(delete(Summary).where(Summary.session_id == 32))
        await db.commit()

    await real_engine.dispose()

    assert summary is not None
    assert summary.session_id == 32
    assert summary.status == "done"
    assert "squat" in summary.exercises_covered
    assert "good form on squat" in summary.coaching_notes
    assert "add hip mobility" in summary.next_session_recommendations


@pytest.mark.asyncio
async def test_generate_summary_writes_failed_status_on_openai_error():
    mock_ctx, mock_db = _make_mock_db(messages=[])

    with patch("agent.summary.AsyncSessionLocal", return_value=mock_ctx), \
         patch("agent.summary.openai_client.chat.completions.create", side_effect=Exception("OpenAI timeout")):
        # Must not raise — failure is swallowed
        await generate_summary(session_id=1)

    mock_db.add.assert_called_once()
    summary_obj = mock_db.add.call_args[0][0]
    assert summary_obj.status == "failed"
