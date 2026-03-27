"""Integration tests: summary retrieval endpoint."""
import pytest
import respx
import httpx
from shared.models import Summary

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_livekit():
    with respx.mock(base_url="https://livekit-api.example.com") as mock:
        mock.post("/twirp/livekit.RoomService/CreateRoom").mock(
            return_value=httpx.Response(200, json={"name": "session-1", "sid": "RM_fake"})
        )
        mock.post("/twirp/livekit.AgentDispatchService/CreateDispatch").mock(
            return_value=httpx.Response(200, json={"dispatch_id": "D_fake"})
        )
        yield mock


async def _create_session_and_end(client, auth_headers, db_session, mock_livekit):
    create_resp = await client.post("/sessions", headers=auth_headers)
    session_id = create_resp.json()["session_id"]
    from shared.models import Session, SessionStatus
    session = await db_session.get(Session, session_id)
    session.status = SessionStatus.ACTIVE
    await db_session.commit()
    with respx.mock() as m:
        m.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={
                "choices": [{"message": {"content": '{"exercises":["squats"],"coaching_notes":["good form"],"next_recommendations":["add lunges"]}'}}]
            })
        )
        await client.post(f"/sessions/{session_id}/end", headers=auth_headers)
    return session_id


async def test_summary_returns_200_when_done(client, auth_headers, db_session, mock_livekit):
    session_id = await _create_session_and_end(client, auth_headers, db_session, mock_livekit)
    resp = await client.get(f"/summaries/{session_id}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "exercises" in body
    assert "coaching_notes" in body
    assert "next_recommendations" in body


async def test_summary_returns_202_when_pending(client, auth_headers, db_session, mock_livekit):
    create_resp = await client.post("/sessions", headers=auth_headers)
    session_id = create_resp.json()["session_id"]
    # Insert a pending summary directly
    pending = Summary(session_id=session_id, status="pending")
    db_session.add(pending)
    await db_session.commit()

    resp = await client.get(f"/summaries/{session_id}", headers=auth_headers)
    assert resp.status_code == 202


async def test_summary_wrong_user_returns_403(client, auth_headers, db_session, mock_livekit):
    session_id = await _create_session_and_end(client, auth_headers, db_session, mock_livekit)

    await client.post("/auth/register", json={"email": "spy@example.com", "password": "StrongPass123!"})
    login = await client.post("/auth/login", json={"email": "spy@example.com", "password": "StrongPass123!"})
    spy_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.get(f"/summaries/{session_id}", headers=spy_headers)
    assert resp.status_code == 403
