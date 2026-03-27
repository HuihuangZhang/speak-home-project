"""Tests for session lifecycle state machine."""
import pytest
from shared.session_state import SessionStatus, can_transition, transition


class TestSessionStateMachine:
    def test_created_to_active(self):
        assert can_transition(SessionStatus.CREATED, SessionStatus.ACTIVE)

    def test_active_to_paused(self):
        assert can_transition(SessionStatus.ACTIVE, SessionStatus.PAUSED)

    def test_paused_to_active(self):
        assert can_transition(SessionStatus.PAUSED, SessionStatus.ACTIVE)

    def test_active_to_completed(self):
        assert can_transition(SessionStatus.ACTIVE, SessionStatus.COMPLETED)

    def test_paused_to_completed(self):
        assert can_transition(SessionStatus.PAUSED, SessionStatus.COMPLETED)

    def test_completed_is_terminal(self):
        for status in SessionStatus:
            if status != SessionStatus.COMPLETED:
                assert not can_transition(SessionStatus.COMPLETED, status)

    def test_created_cannot_jump_to_completed(self):
        assert not can_transition(SessionStatus.CREATED, SessionStatus.COMPLETED)

    def test_transition_raises_on_invalid(self):
        with pytest.raises(ValueError, match="Invalid transition"):
            transition(SessionStatus.COMPLETED, SessionStatus.ACTIVE)
