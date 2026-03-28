"""LiveKit Agent Worker entry point."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
    llm,
)
from livekit.plugins import deepgram, openai, silero

from agent.tutor import SYSTEM_PROMPT, load_session_context, parse_dispatch_metadata, save_transcript_turn
from agent.tools import get_user_fitness_history, log_session_note, save_exercise_plan
from agent.summary import generate_summary
from shared.config import settings
from shared.db import AsyncSessionLocal
from shared.models import Session
from shared.session_state import SessionStatus

logger = logging.getLogger(__name__)


async def entrypoint(ctx: JobContext) -> None:
    """Called when a new job (session room) is dispatched to this worker."""
    logger.info("=== Job received | room=%s job_id=%s ===", ctx.room.name, ctx.job.id)

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info("Connected to room | room=%s participants=%d", ctx.room.name, len(ctx.room.remote_participants))

    # Parse metadata sent by the API at dispatch time
    raw_metadata = json.loads(ctx.job.metadata or "{}")
    logger.info("Dispatch metadata | raw=%s", raw_metadata)
    session_id, user_id = parse_dispatch_metadata(raw_metadata)
    logger.info("Parsed metadata | session_id=%d user_id=%d", session_id, user_id)

    # Load conversation history + exercise plan for resumability
    logger.info("Loading session context | session_id=%d", session_id)
    async with AsyncSessionLocal() as db:
        context = await load_session_context(db=db, session_id=session_id)
    logger.info(
        "Session context loaded | session_id=%d messages=%d has_plan=%s",
        session_id, len(context["messages"]), context["exercise_plan"] is not None,
    )

    # Build initial chat context
    system_text = SYSTEM_PROMPT + (
        f"\n\nPrevious exercise plan: {json.dumps(context['exercise_plan'])}"
        if context["exercise_plan"]
        else ""
    )
    initial_ctx = llm.ChatContext()
    initial_ctx.add_message(role="system", content=system_text)
    for m in context["messages"]:
        initial_ctx.add_message(role=m["role"], content=m["content"])
    logger.info("Chat context built | system_chars=%d history_msgs=%d", len(system_text), len(context["messages"]))

    # Define LLM tools using function_tool decorator
    @function_tool
    async def _save_plan(plan_json: str) -> str:
        """Save the exercise plan for this session. Call with a JSON string."""
        logger.info("Tool: save_plan called | session_id=%d plan_json=%s", session_id, plan_json[:200])
        try:
            plan = json.loads(plan_json)
            async with AsyncSessionLocal() as db:
                await save_exercise_plan(db=db, session_id=session_id, plan=plan)
            logger.info("Tool: save_plan success | session_id=%d", session_id)
            return "Exercise plan saved successfully."
        except Exception as exc:
            logger.error("Tool: save_plan failed | session_id=%d error=%s", session_id, exc)
            return f"Error saving plan: {exc}"

    @function_tool
    async def _log_note(note: str) -> str:
        """Log a coaching note for this session."""
        logger.info("Tool: log_note called | session_id=%d note=%s", session_id, note[:200])
        async with AsyncSessionLocal() as db:
            await log_session_note(
                db=db, session_id=session_id, role="note", content=note
            )
        logger.info("Tool: log_note success | session_id=%d", session_id)
        return "Note logged."

    @function_tool
    async def _get_history() -> str:
        """Get user's fitness history from previous sessions."""
        logger.info("Tool: get_history called | user_id=%d", user_id)
        async with AsyncSessionLocal() as db:
            msgs = await get_user_fitness_history(db=db, user_id=user_id, limit=20)
        logger.info("Tool: get_history returned %d messages | user_id=%d", len(msgs), user_id)
        return json.dumps([{"role": m.role, "content": m.content} for m in msgs])

    # Build agent with instructions, tools, and history
    agent = Agent(
        instructions=system_text,
        chat_ctx=initial_ctx,
        tools=[_save_plan, _log_note, _get_history],
    )
    logger.info("Agent built | session_id=%d", session_id)

    # Build voice pipeline session
    logger.info("Building voice pipeline | stt=deepgram llm=gpt-4o-mini tts=openai")
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(api_key=settings.deepgram_api_key),
        llm=openai.LLM(model="gpt-4o-mini", api_key=settings.openai_api_key),
        tts=openai.TTS(api_key=settings.openai_api_key),
    )

    await session.start(agent, room=ctx.room)
    logger.info("Agent session started | session_id=%d room=%s", session_id, ctx.room.name)

    # Log every STT word/phrase as it arrives from LiveKit (partial and final).
    # This is the earliest point you can see what the user said.
    @session.on("user_input_transcribed")
    def on_user_input_transcribed(event) -> None:
        logger.info(
            "STT transcript | session_id=%d is_final=%s text=%r",
            session_id, event.is_final, event.transcript,
        )

    # Persist every finalized conversation turn (user + assistant) to the messages table.
    # conversation_item_added fires once per ChatMessage after speech is committed.
    @session.on("conversation_item_added")
    def on_conversation_item_added(event) -> None:
        item = event.item
        if not isinstance(item, llm.ChatMessage):
            return  # skip function_call / function_call_output items
        if item.role not in ("user", "assistant"):
            return  # skip system messages
        if item.interrupted:
            return  # skip partial agent utterances that were cut off
        text = item.text_content
        if not text:
            return

        async def _persist() -> None:
            async with AsyncSessionLocal() as db:
                await save_transcript_turn(db=db, session_id=session_id, role=item.role, content=text)

        asyncio.create_task(_persist())
        logger.info(
            "conversation_item_added → persisting | session_id=%d role=%s text=%r",
            session_id, item.role, text,
        )

    greeting = (
        "Welcome back! Let's pick up where we left off."
        if context["messages"]
        else "Hi! I'm Alex, your personal fitness coach. What are your fitness goals today?"
    )
    logger.info("Saying greeting | session_id=%d resuming=%s", session_id, bool(context["messages"]))
    await session.say(greeting, allow_interruptions=True)

    # Handle participant disconnect → pause timeout logic
    pause_timeout = settings.session_pause_timeout_minutes * 60

    @ctx.room.on("participant_disconnected")
    def on_disconnect(_participant):
        logger.info(
            "Participant disconnected | session_id=%d participant=%s",
            session_id, getattr(_participant, "identity", "unknown"),
        )

        async def _handle_pause():
            async with AsyncSessionLocal() as db:
                session_obj = await db.get(Session, session_id)
                if session_obj and session_obj.status == SessionStatus.ACTIVE:
                    session_obj.status = SessionStatus.PAUSED
                    session_obj.paused_at = datetime.now(timezone.utc)
                    await db.commit()
                    logger.info("Session paused | session_id=%d", session_id)

            logger.info(
                "Waiting %ds for reconnect | session_id=%d",
                pause_timeout, session_id,
            )
            # Shield the sleep so LiveKit job cancellation doesn't abort the timeout
            try:
                await asyncio.shield(asyncio.sleep(pause_timeout))
            except asyncio.CancelledError:
                logger.info("_handle_pause shielded — continuing after cancel | session_id=%d", session_id)

            # Check if still paused (user might have reconnected)
            async with AsyncSessionLocal() as db:
                session_obj = await db.get(Session, session_id)
                if session_obj and session_obj.status == SessionStatus.PAUSED:
                    logger.info("Reconnect timeout — completing session | session_id=%d", session_id)
                    session_obj.status = SessionStatus.COMPLETED
                    session_obj.ended_at = datetime.now(timezone.utc)
                    await db.commit()
                else:
                    logger.info("Session reconnected or already completed | session_id=%d", session_id)
                    return

            # Run summary in a fresh task so it outlives any room disconnect
            asyncio.ensure_future(generate_summary(session_id=session_id))
            logger.info("generate_summary scheduled | session_id=%d", session_id)

            await ctx.room.disconnect()

        asyncio.create_task(_handle_pause())


def main():
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="exercise-tutor",
            ws_url=settings.livekit_url,
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        )
    )


if __name__ == "__main__":
    main()
