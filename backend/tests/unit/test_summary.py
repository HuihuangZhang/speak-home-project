"""Tests for post-session summary generation."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from agent.summary import generate_summary, build_summary_prompt


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


@pytest.mark.asyncio
async def test_generate_summary_writes_done_status():
    mock_db = AsyncMock()
    mock_messages_result = MagicMock()
    mock_messages_result.scalars.return_value.all.return_value = [
        MagicMock(role="user", content="I want to lose weight"),
        MagicMock(role="assistant", content="Here is your plan"),
    ]
    mock_db.execute.return_value = mock_messages_result
    mock_db.get.return_value = None  # no existing summary

    openai_response = MagicMock()
    openai_response.choices[0].message.content = (
        '{"exercises": ["running"], "coaching_notes": ["good pace"], "next_recommendations": ["add strength"]}'
    )

    with patch("agent.summary.openai_client.chat.completions.create", return_value=openai_response):
        await generate_summary(db=mock_db, session_id=1)

    mock_db.add.assert_called_once()
    summary_obj = mock_db.add.call_args[0][0]
    assert summary_obj.status == "done"
    assert summary_obj.session_id == 1


@pytest.mark.asyncio
async def test_generate_summary_writes_failed_status_on_openai_error():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    mock_db.get.return_value = None

    with patch("agent.summary.openai_client.chat.completions.create", side_effect=Exception("OpenAI timeout")):
        # Must not raise — failure is swallowed
        await generate_summary(db=mock_db, session_id=1)

    mock_db.add.assert_called_once()
    summary_obj = mock_db.add.call_args[0][0]
    assert summary_obj.status == "failed"
