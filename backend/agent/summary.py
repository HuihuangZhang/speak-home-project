"""Post-session summary generation."""
import asyncio
import json
import logging
from datetime import datetime, timezone

from openai import OpenAI
from sqlalchemy import select

from shared.config import settings
from shared.db import AsyncSessionLocal
from shared.models import Message, Summary

logger = logging.getLogger(__name__)

# Module-level sync client — patched in unit tests via
# `patch("agent.summary.openai_client.chat.completions.create", ...)`
openai_client = OpenAI(api_key=settings.openai_api_key)


def build_summary_prompt(messages: list[dict]) -> str:
    transcript = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in messages
    )
    return (
        "Analyze this fitness coaching session transcript and generate a structured summary.\n\n"
        f"Transcript:\n{transcript}\n\n"
        "Please provide a JSON response with these exact keys:\n"
        "- exercises: list of exercises covered (strings)\n"
        "- coaching_notes: list of key coaching observations\n"
        "- next_recommendations: list of recommendations for the next session\n\n"
        "Focus on what exercises were discussed, form cues given, and next session recommendations."
    )


async def generate_summary(session_id: int) -> None:
    """Generate a post-session summary and persist it. Never raises."""
    logger.info("generate_summary started | session_id=%d", session_id)
    async with AsyncSessionLocal() as db:
        try:
            # Fetch full transcript
            result = await db.execute(
                select(Message)
                .where(Message.session_id == session_id)
                .order_by(Message.created_at.asc())
            )
            messages = result.scalars().all()
            logger.info("generate_summary | session_id=%d transcript_messages=%d", session_id, len(messages))

            prompt = build_summary_prompt(
                [{"role": m.role, "content": m.content} for m in messages]
            )

            logger.info("generate_summary calling OpenAI | session_id=%d promp=%s", session_id, prompt)
            # Call OpenAI synchronously in a thread pool so unit-test mocks work
            response = await asyncio.to_thread(
                openai_client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            content = json.loads(response.choices[0].message.content)
            logger.info(
                "generate_summary OpenAI response | session_id=%d exercises=%d notes=%d recommendations=%d",
                session_id,
                len(content.get("exercises", [])),
                len(content.get("coaching_notes", [])),
                len(content.get("next_recommendations", [])),
            )

            summary = Summary(
                session_id=session_id,
                exercises_covered=content.get("exercises", []),
                coaching_notes=", ".join(content.get("coaching_notes", [])),
                next_session_recommendations=", ".join(
                    content.get("next_recommendations", [])
                ),
                status="done",
                generated_at=datetime.now(timezone.utc),
            )
            logger.info("generate_summary done | session_id=%d", session_id)
        except Exception as exc:
            logger.error("generate_summary failed | session_id=%d error=%s", session_id, exc, exc_info=True)
            summary = Summary(session_id=session_id, status="failed")

        db.add(summary)
        await db.commit()
        logger.info("generate_summary committed | session_id=%d status=%s", session_id, summary.status)
