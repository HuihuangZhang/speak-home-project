"""Exercise tutor agent persona and session context helpers."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import Message, Session

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Alex, a professional fitness coach and personal trainer.

Your role is to:
- Give personalized exercise plans based on the user's goals and fitness level
- Suggest specific exercises with sets, reps, and duration
- Motivate and encourage the user throughout their workout
- Prioritize safety: always ask about injuries or limitations before suggesting exercises
- Be warm, encouraging, and specific in your coaching cues

When a user describes their goals:
1. Ask about any injuries or physical limitations
2. Assess their current fitness level
3. Propose a structured workout plan
4. Guide them through each exercise with clear instructions

Always call save_exercise_plan when you finalize a plan with the user."""


def parse_dispatch_metadata(raw_metadata: dict) -> tuple[int, int]:
    """Parse session_id and user_id from LiveKit dispatch metadata.

    Raises KeyError if required keys are missing.
    """
    session_id = int(raw_metadata["session_id"])
    user_id = int(raw_metadata["user_id"])
    logger.debug("parse_dispatch_metadata | session_id=%d user_id=%d", session_id, user_id)
    return session_id, user_id


async def load_session_context(db: AsyncSession, session_id: int) -> dict[str, Any]:
    """Load the last 20 messages and exercise plan for a session."""
    logger.debug("load_session_context | session_id=%d", session_id)

    # Fetch last 20 messages ordered by id (insertion order)
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.id.desc())
        .limit(40)
    )
    messages = list(reversed(result.scalars().all()))

    session = await db.get(Session, session_id)
    exercise_plan = session.exercise_plan if session else None

    logger.debug(
        "load_session_context done | session_id=%d messages=%d has_plan=%s",
        session_id, len(messages), exercise_plan is not None,
    )
    return {
        "messages": [{"role": m.role, "content": m.content} for m in messages],
        "exercise_plan": exercise_plan,
    }


async def save_transcript_turn(
    db: AsyncSession, session_id: int, role: str, content: str
) -> None:
    """Persist a single conversation turn to the messages table."""
    logger.debug("save_transcript_turn | session_id=%d role=%s chars=%d", session_id, role, len(content))
    from shared.models import Message as Msg

    msg = Msg(session_id=session_id, role=role, content=content)
    db.add(msg)
    await db.commit()
    logger.debug("save_transcript_turn committed | session_id=%d role=%s", session_id, role)
