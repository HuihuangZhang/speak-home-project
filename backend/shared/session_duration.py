"""Active session duration: wall time from created_at minus PAUSED intervals."""

from datetime import datetime, timezone
from typing import Optional

from shared.models import Session
from shared.session_state import SessionStatus


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def compute_duration_seconds(
    *,
    created_at: datetime,
    ended_at: Optional[datetime],
    status: SessionStatus,
    paused_at: Optional[datetime],
    total_paused_seconds: int,
    now: datetime,
) -> int:
    """Active seconds for in-flight sessions (COMPLETED rows should use stored duration_seconds)."""
    created = ensure_utc(created_at)
    now_utc = ensure_utc(now)
    wall_end = ensure_utc(ended_at) if status == SessionStatus.COMPLETED and ended_at else now_utc
    wall_sec = max(0, int((wall_end - created).total_seconds()))
    pause_extra = 0
    if status == SessionStatus.PAUSED and paused_at is not None:
        p = ensure_utc(paused_at)
        pause_extra = max(0, int((now_utc - p).total_seconds()))
    pause_total = int(total_paused_seconds) + pause_extra
    return max(0, wall_sec - pause_total)


def accumulate_pause_before_resume(session: Session, resume_at: datetime) -> None:
    """Add the current PAUSED segment to total_paused_seconds; clear paused_at after caller commits."""
    if session.paused_at is None:
        return
    p = ensure_utc(session.paused_at)
    r = ensure_utc(resume_at)
    session.total_paused_seconds = (session.total_paused_seconds or 0) + max(
        0, int((r - p).total_seconds())
    )


def finalize_completed_session(session: Session, ended_at: datetime) -> None:
    """Fold open pause into totals, clear paused_at, set duration_seconds. Caller sets status COMPLETED."""
    ended = ensure_utc(ended_at)
    if session.status == SessionStatus.PAUSED and session.paused_at is not None:
        p = ensure_utc(session.paused_at)
        session.total_paused_seconds = (session.total_paused_seconds or 0) + max(
            0, int((ended - p).total_seconds())
        )
        session.paused_at = None
    created = ensure_utc(session.created_at)
    wall_sec = max(0, int((ended - created).total_seconds()))
    session.duration_seconds = max(0, wall_sec - (session.total_paused_seconds or 0))


def duration_seconds_for_api(session: Session, now: datetime) -> int:
    """Value exposed on list/detail: stored when completed, else computed live."""
    if session.status == SessionStatus.COMPLETED:
        if session.duration_seconds is not None:
            return int(session.duration_seconds)
        return compute_duration_seconds(
            created_at=session.created_at,
            ended_at=session.ended_at,
            status=SessionStatus.COMPLETED,
            paused_at=session.paused_at,
            total_paused_seconds=session.total_paused_seconds or 0,
            now=now,
        )
    return compute_duration_seconds(
        created_at=session.created_at,
        ended_at=session.ended_at,
        status=session.status,
        paused_at=session.paused_at,
        total_paused_seconds=session.total_paused_seconds or 0,
        now=now,
    )
