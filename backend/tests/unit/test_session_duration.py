"""Unit tests for active session duration helpers."""
from datetime import datetime, timedelta, timezone

from shared.session_duration import compute_duration_seconds, finalize_completed_session
from shared.session_state import SessionStatus


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def test_compute_active_no_pause():
    created = _dt("2026-01-01T12:00:00+00:00")
    now = _dt("2026-01-01T12:05:30+00:00")
    assert (
        compute_duration_seconds(
            created_at=created,
            ended_at=None,
            status=SessionStatus.ACTIVE,
            paused_at=None,
            total_paused_seconds=0,
            now=now,
        )
        == 330
    )


def test_compute_excludes_current_pause():
    created = _dt("2026-01-01T12:00:00+00:00")
    paused_at = _dt("2026-01-01T12:03:00+00:00")
    now = _dt("2026-01-01T12:05:00+00:00")
    # Active 3m, paused 2m → 180s
    assert (
        compute_duration_seconds(
            created_at=created,
            ended_at=None,
            status=SessionStatus.PAUSED,
            paused_at=paused_at,
            total_paused_seconds=0,
            now=now,
        )
        == 180
    )


def test_compute_excludes_completed_pause_segments():
    created = _dt("2026-01-01T12:00:00+00:00")
    now = _dt("2026-01-01T12:10:00+00:00")
    assert (
        compute_duration_seconds(
            created_at=created,
            ended_at=None,
            status=SessionStatus.ACTIVE,
            paused_at=None,
            total_paused_seconds=120,
            now=now,
        )
        == 480
    )


def test_finalize_completed_while_paused():
    class _S:
        pass

    s = _S()
    s.status = SessionStatus.PAUSED
    s.created_at = _dt("2026-01-01T12:00:00+00:00")
    s.paused_at = _dt("2026-01-01T12:08:00+00:00")
    s.total_paused_seconds = 60
    ended = _dt("2026-01-01T12:10:00+00:00")
    finalize_completed_session(s, ended)
    assert s.paused_at is None
    assert s.total_paused_seconds == 60 + 120
    # wall 600 - total paused 180 = 420
    assert s.duration_seconds == 420


def test_finalize_completed_while_active():
    class _S:
        pass

    s = _S()
    s.status = SessionStatus.ACTIVE
    s.created_at = _dt("2026-01-01T12:00:00+00:00")
    s.paused_at = None
    s.total_paused_seconds = 90
    ended = _dt("2026-01-01T12:05:00+00:00")
    finalize_completed_session(s, ended)
    assert s.duration_seconds == 300 - 90


def test_compute_paused_duration_stable_with_subseconds():
    # Created at and paused_at with microseconds should yield a stable integer duration
    created = _dt("2026-04-16T13:03:58.087272+00:00")
    paused_at = _dt("2026-04-16T13:04:44.416457+00:00")

    # Now can be any time after paused_at; active time should be floor(paused_at - created)
    now = _dt("2026-04-16T13:05:00.000000+00:00")
    dur = compute_duration_seconds(
        created_at=created,
        ended_at=None,
        status=SessionStatus.PAUSED,
        paused_at=paused_at,
        total_paused_seconds=0,
        now=now,
    )
    assert dur == 46
