from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Optional

from api.deps import get_current_user
from shared.db import get_db
from shared.models import Session, Summary, User

router = APIRouter(prefix="/summaries", tags=["summaries"])


class SummaryResponse(BaseModel):
    session_id: int
    exercises: Optional[Any]
    coaching_notes: Optional[str]
    next_recommendations: Optional[str]
    status: str


@router.get("/{session_id}")
async def get_summary(
    session_id: int,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify session ownership
    session = await db.get(Session, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    result = await db.execute(
        select(Summary).where(Summary.session_id == session_id)
    )
    summary = result.scalar_one_or_none()

    if summary is None or summary.status == "pending":
        response.status_code = status.HTTP_202_ACCEPTED
        return {"status": "pending"}

    return SummaryResponse(
        session_id=summary.session_id,
        exercises=summary.exercises_covered,
        coaching_notes=summary.coaching_notes,
        next_recommendations=summary.next_session_recommendations,
        status=summary.status,
    )
