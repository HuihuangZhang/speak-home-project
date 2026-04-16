"""Integration tests: session lifecycle endpoints."""
import pytest
import respx
import httpx
from datetime import datetime, timedelta, timezone

pytestmark = pytest.mark.asyncio

LIVEKIT_TOKEN = "lk.fake.token"
LIVEKIT_ROOM = "session-1"


@pytest.fixture
def mock_livekit():
    """Mock LiveKit API calls (room create + agent dispatch + token generation)."""
    with respx.mock(base_url="https://livekit-api.example.com") as mock:
        # Room creation
        mock.post("/twirp/livekit.RoomService/CreateRoom").mock(
            return_value=httpx.Response(200, json={"name": LIVEKIT_ROOM, "sid": "RM_fake"})
        )
        # Agent dispatch
        mock.post("/twirp/livekit.AgentDispatchService/CreateDispatch").mock(
            return_value=httpx.Response(200, json={"dispatch_id": "D_fake"})
        )
        yield mock


async def test_create_session_returns_livekit_token(client, auth_headers, mock_livekit):
    resp = await client.post("/sessions", headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert "session_id" in body
    assert "livekit_token" in body
    assert "room_name" in body
    assert body["room_name"].startswith("session-")


async def test_create_session_dispatches_agent(client, auth_headers, mock_livekit):
    await client.post("/sessions", headers=auth_headers)
    # Agent dispatch endpoint must have been called exactly once
    dispatch_calls = [r for r in mock_livekit.calls if "AgentDispatchService/CreateDispatch" in str(r.request.url)]
    assert len(dispatch_calls) == 1


async def test_get_sessions_list(client, auth_headers, mock_livekit):
    await client.post("/sessions", headers=auth_headers)
    await client.post("/sessions", headers=auth_headers)
    resp = await client.get("/sessions", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 2
    for item in body["items"]:
        assert "duration_seconds" in item


async def test_get_session_by_id(client, auth_headers, mock_livekit):
    create_resp = await client.post("/sessions", headers=auth_headers)
    session_id = create_resp.json()["session_id"]
    resp = await client.get(f"/sessions/{session_id}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == session_id
    assert "duration_seconds" in body
    assert isinstance(body["duration_seconds"], int)


async def test_get_session_wrong_user_returns_403(client, auth_headers, mock_livekit):
    # Create session as user1
    create_resp = await client.post("/sessions", headers=auth_headers)
    session_id = create_resp.json()["session_id"]

    # Register and login as user2
    await client.post("/auth/register", json={"email": "other@example.com", "password": "StrongPass123!"})
    login_resp = await client.post("/auth/login", json={"email": "other@example.com", "password": "StrongPass123!"})
    other_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    resp = await client.get(f"/sessions/{session_id}", headers=other_headers)
    assert resp.status_code == 403


async def test_reconnect_paused_session_succeeds(client, auth_headers, mock_livekit, db_session):
    create_resp = await client.post("/sessions", headers=auth_headers)
    session_id = create_resp.json()["session_id"]

    # Force session to PAUSED state in DB
    from shared.models import Session, SessionStatus
    session = await db_session.get(Session, session_id)
    session.status = SessionStatus.PAUSED
    session.paused_at = datetime.now(timezone.utc)
    await db_session.commit()

    resp = await client.post(f"/sessions/{session_id}/reconnect", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "livekit_token" in body
    assert body["status"] == "ACTIVE"
    await db_session.refresh(session)
    assert session.total_paused_seconds >= 0
    assert session.paused_at is None


async def test_reconnect_expired_paused_session_returns_409(client, auth_headers, mock_livekit, db_session):
    create_resp = await client.post("/sessions", headers=auth_headers)
    session_id = create_resp.json()["session_id"]

    from shared.models import Session, SessionStatus
    session = await db_session.get(Session, session_id)
    session.status = SessionStatus.PAUSED
    # Paused 10 minutes ago — beyond the 5-minute window
    session.paused_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    await db_session.commit()

    resp = await client.post(f"/sessions/{session_id}/reconnect", headers=auth_headers)
    assert resp.status_code == 409
    assert "expired" in resp.json()["detail"].lower()


async def test_reconnect_completed_session_returns_409(client, auth_headers, mock_livekit, db_session):
    create_resp = await client.post("/sessions", headers=auth_headers)
    session_id = create_resp.json()["session_id"]

    from shared.models import Session, SessionStatus
    session = await db_session.get(Session, session_id)
    session.status = SessionStatus.COMPLETED
    await db_session.commit()

    resp = await client.post(f"/sessions/{session_id}/reconnect", headers=auth_headers)
    assert resp.status_code == 409


async def test_end_session_sets_completed(client, auth_headers, mock_livekit, db_session):
    create_resp = await client.post("/sessions", headers=auth_headers)
    session_id = create_resp.json()["session_id"]

    # Move to ACTIVE
    from shared.models import Session, SessionStatus
    session = await db_session.get(Session, session_id)
    session.status = SessionStatus.ACTIVE
    await db_session.commit()

    with respx.mock() as openai_mock:
        openai_mock.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={
                "choices": [{"message": {"content": '{"exercises":[],"coaching_notes":[],"next_recommendations":[]}'}}]
            })
        )
        resp = await client.post(f"/sessions/{session_id}/end", headers=auth_headers)

    assert resp.status_code == 200
    await db_session.refresh(session)
    assert session.status == SessionStatus.COMPLETED
    assert session.duration_seconds is not None
    assert session.duration_seconds >= 0

    detail = await client.get(f"/sessions/{session_id}", headers=auth_headers)
    assert detail.json()["duration_seconds"] == session.duration_seconds
