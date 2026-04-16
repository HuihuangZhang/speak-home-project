import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from jose import jwt as jose_jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_current_user_unless_test_utils
from shared.config import settings
from shared.db import get_db
from shared.models import Message, Session, Summary, User
from shared.session_state import SessionStatus, transition

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["sessions"])


# ---------------------------------------------------------------------------
# LiveKit helpers (use httpx directly so respx can mock in tests)
# ---------------------------------------------------------------------------


def _livekit_api_jwt() -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "iss": settings.livekit_api_key,
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=2)).timestamp()),
        "video": {"roomCreate": True, "roomAdmin": True, "roomJoin": True},
    }
    return jose_jwt.encode(payload, settings.livekit_api_secret, algorithm="HS256")


def _user_livekit_token(room_name: str, user_identity: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "iss": settings.livekit_api_key,
        "sub": user_identity,
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(hours=2)).timestamp()),
        "video": {"roomJoin": True, "room": room_name},
    }
    return jose_jwt.encode(payload, settings.livekit_api_secret, algorithm="HS256")


async def _create_livekit_room(room_name: str) -> None:
    url = f"{settings.livekit_api_url}/twirp/livekit.RoomService/CreateRoom"
    logger.info("Creating LiveKit room | url=%s room=%s", url, room_name)
    jwt = _livekit_api_jwt()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json={"name": room_name},
            headers={
                "Authorization": f"Bearer {jwt}",
                "Content-Type": "application/json",
            },
        )
        logger.info("CreateRoom response | status=%d body=%s", resp.status_code, resp.text[:500])
        resp.raise_for_status()


def _livekit_dispatch_jwt(room_name: str) -> str:
    """JWT for AgentDispatchService — must include the specific room name."""
    now = datetime.now(timezone.utc)
    payload = {
        "iss": settings.livekit_api_key,
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=2)).timestamp()),
        "video": {"roomAdmin": True, "room": room_name},
    }
    return jose_jwt.encode(payload, settings.livekit_api_secret, algorithm="HS256")


async def _dispatch_agent(room_name: str, session_id: int, user_id: int) -> None:
    url = f"{settings.livekit_api_url}/twirp/livekit.AgentDispatchService/CreateDispatch"
    payload = {
        "room": room_name,
        "agent_name": "exercise-tutor",
        "metadata": json.dumps({"session_id": str(session_id), "user_id": str(user_id)}),
    }
    logger.info("Dispatching agent | url=%s payload=%s", url, payload)
    jwt = _livekit_dispatch_jwt(room_name)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {jwt}",
                "Content-Type": "application/json",
            },
        )
        logger.info("CreateDispatch response | status=%d body=%s", resp.status_code, resp.text[:500])
        resp.raise_for_status()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class SessionCreateResponse(BaseModel):
    session_id: int
    livekit_token: str
    room_name: str


class SessionItem(BaseModel):
    id: int
    room_name: str
    status: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]


class SessionListResponse(BaseModel):
    items: list[SessionItem]


class SessionDetailResponse(BaseModel):
    id: int
    room_name: str
    status: str
    exercise_plan: Optional[Any]
    started_at: Optional[datetime]
    paused_at: Optional[datetime]
    ended_at: Optional[datetime]


class ReconnectResponse(BaseModel):
    livekit_token: str
    status: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = Session(
        user_id=current_user.id,
        status=SessionStatus.CREATED,
        room_name="pending",  # placeholder until we have the ID
    )
    db.add(session)
    await db.flush()

    room_name = f"session-{session.id}"
    session.room_name = room_name
    await db.commit()

    try:
        await _create_livekit_room(room_name)
        await _dispatch_agent(room_name, session.id, current_user.id)
    except Exception as exc:
        logger.error("LiveKit provisioning failed for room %s: %s", room_name, exc, exc_info=True)
        await db.delete(session)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LiveKit provisioning failed: {exc}",
        )

    session.status = SessionStatus.ACTIVE
    await db.commit()

    token = _user_livekit_token(room_name, str(current_user.id))
    return SessionCreateResponse(
        session_id=session.id,
        livekit_token=token,
        room_name=room_name,
    )


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Session)
        .where(Session.user_id == current_user.id)
        .order_by(Session.started_at.desc())
    )
    sessions = result.scalars().all()
    items = [
        SessionItem(
            id=s.id,
            room_name=s.room_name,
            status=s.status.value,
            started_at=s.started_at,
            ended_at=s.ended_at,
        )
        for s in sessions
    ]
    return SessionListResponse(items=items)


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await db.get(Session, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return SessionDetailResponse(
        id=session.id,
        room_name=session.room_name,
        status=session.status.value,
        exercise_plan=session.exercise_plan,
        started_at=session.started_at,
        paused_at=session.paused_at,
        ended_at=session.ended_at,
    )


@router.post("/{session_id}/reconnect", response_model=ReconnectResponse)
async def reconnect_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await db.get(Session, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Allow re-joining an active session with a fresh token
    if session.status == SessionStatus.ACTIVE:
        token = _user_livekit_token(session.room_name, str(current_user.id))
        return ReconnectResponse(livekit_token=token, status=SessionStatus.ACTIVE.value)

    if session.status != SessionStatus.PAUSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session is not paused or has expired",
        )

    # Check pause timeout
    if session.paused_at:
        elapsed = datetime.now(timezone.utc) - session.paused_at.replace(
            tzinfo=timezone.utc
        ) if session.paused_at.tzinfo is None else datetime.now(timezone.utc) - session.paused_at
        if elapsed > timedelta(minutes=settings.session_pause_timeout_minutes):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Session has expired — please start a new session",
            )

    session.status = transition(session.status, SessionStatus.ACTIVE)
    session.paused_at = None
    await db.commit()

    token = _user_livekit_token(session.room_name, str(current_user.id))
    return ReconnectResponse(livekit_token=token, status=SessionStatus.ACTIVE.value)


@router.post("/{session_id}/end")
async def end_session(
    session_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await db.get(Session, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    session.status = SessionStatus.COMPLETED
    session.ended_at = datetime.now(timezone.utc)
    await db.commit()

    # Trigger summary generation as a background task
    from agent.summary import generate_summary  # avoid circular at module level

    background_tasks.add_task(generate_summary, session_id)
    return {"status": "completed"}


@router.post("/{session_id}/force-expire")
async def force_expire_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_unless_test_utils),
):
    """Force a session into PAUSED with an expired paused_at (E2E / dev). Requires auth unless ENABLE_TEST_UTILS."""
    session = await db.get(Session, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if not settings.enable_test_utils:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        if session.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    session.status = SessionStatus.PAUSED
    session.paused_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    await db.commit()
    return {"status": "force-expired"}
