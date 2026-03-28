"""LLM-callable tools for the exercise tutor agent."""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import Message, Session, SessionStatus

logger = logging.getLogger(__name__)


async def save_exercise_plan(db: AsyncSession, session_id: int, plan: dict) -> None:
    """Persist the exercise plan to the current session record."""
    logger.info("save_exercise_plan | session_id=%d plan_keys=%s", session_id, list(plan.keys()))
    session = await db.get(Session, session_id)
    if session is None:
        logger.error("save_exercise_plan | session_id=%d not found", session_id)
        raise ValueError(f"Session {session_id} not found")
    session.exercise_plan = plan
    await db.commit()
    logger.info("save_exercise_plan committed | session_id=%d", session_id)


async def log_session_note(
    db: AsyncSession, session_id: int, role: str, content: str
) -> None:
    """Write a coaching note into the messages table."""
    logger.info("log_session_note | session_id=%d role=%s chars=%d", session_id, role, len(content))
    note = Message(session_id=session_id, role=role, content=content)
    db.add(note)
    await db.commit()
    logger.debug("log_session_note committed | session_id=%d", session_id)


async def get_user_fitness_history(
    db: AsyncSession, user_id: int, limit: int = 20
) -> list:
    """Return the last N messages across the user's sessions for context."""
    logger.info("get_user_fitness_history | user_id=%d limit=%d", user_id, limit)
    result = await db.execute(
        select(Message)
        .join(Session, Message.session_id == Session.id)
        .where(Session.user_id == user_id)
        .order_by(Message.id.desc())
        .limit(limit)
    )
    msgs = result.scalars().all()
    logger.info("get_user_fitness_history returned %d messages | user_id=%d", len(msgs), user_id)
    return msgs
