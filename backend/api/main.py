import logging
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import auth, sessions, summaries

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(title="Speak Home API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(summaries.router)


# ---------------------------------------------------------------------------
# Test utilities (only for E2E test convenience — not for production)
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from shared.db import get_db
from shared.models import Session as SessionModel
from shared.session_state import SessionStatus

_test_router = APIRouter(prefix="/test-utils", tags=["test-utils"])


@_test_router.post("/sessions/{session_id}/force-expire")
async def force_expire_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Force a session into PAUSED state with an expired paused_at timestamp.
    Used only by E2E tests to simulate timeout without waiting.
    """
    session = await db.get(SessionModel, session_id)
    if session is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    session.status = SessionStatus.PAUSED
    session.paused_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    await db.commit()
    return {"status": "force-expired"}


app.include_router(_test_router)
