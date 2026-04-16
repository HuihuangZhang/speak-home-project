"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  LiveKitRoom,
  useConnectionState,
  RoomAudioRenderer,
  useLocalParticipant,
} from "@livekit/components-react";
import { ConnectionState } from "livekit-client";
import { api } from "@/lib/api";
import { SessionSummary } from "./summary";

const LIVEKIT_URL = process.env.NEXT_PUBLIC_LIVEKIT_URL ?? "";

function SessionControls({
  onEnd,
  roomName,
}: {
  onEnd: () => void;
  roomName: string;
}) {
  const connectionState = useConnectionState();
  const { localParticipant } = useLocalParticipant();
  const [micEnabled, setMicEnabled] = useState(true);

  const statusLabel =
    connectionState === ConnectionState.Connected
      ? "Connected"
      : connectionState === ConnectionState.Connecting
      ? "Connecting…"
      : connectionState === ConnectionState.Reconnecting
      ? "Reconnecting…"
      : "Disconnected";

  async function toggleMic() {
    await localParticipant.setMicrophoneEnabled(!micEnabled);
    setMicEnabled(!micEnabled);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <span
          data-testid="connection-status"
          style={{
            padding: "4px 12px",
            borderRadius: 20,
            background: connectionState === ConnectionState.Connected ? "#d1fae5" : "#fee2e2",
            color: connectionState === ConnectionState.Connected ? "#065f46" : "#991b1b",
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          {statusLabel}
        </span>
        <span data-testid="room-name" style={{ fontSize: 13, color: "#6b7280" }}>
          {roomName}
        </span>
      </div>

      <div style={{ display: "flex", gap: 12 }}>
        <button
          onClick={toggleMic}
          aria-label={micEnabled ? "Microphone on" : "Microphone off"}
          style={{
            padding: "10px 20px",
            background: micEnabled ? "#6366f1" : "#e5e7eb",
            color: micEnabled ? "#fff" : "#374151",
            border: "none",
            borderRadius: 8,
            cursor: "pointer",
          }}
        >
          {micEnabled ? "🎤 Microphone" : "🎤 Mic Off"}
        </button>

        <button
          onClick={onEnd}
          style={{ padding: "10px 20px", background: "#dc2626", color: "#fff", border: "none", borderRadius: 8, cursor: "pointer" }}
        >
          End Session
        </button>
      </div>
    </div>
  );
}

export default function SessionPage() {
  const { id } = useParams<{ id: string }>();
  const sessionId = parseInt(id, 10);
  const router = useRouter();

  const [token, setToken] = useState<string | null>(null);
  const [roomName, setRoomName] = useState("");
  const [ended, setEnded] = useState(false);
  const [error, setError] = useState("");
  const reconnectAttemptRef = useRef(false);

  useEffect(() => {
    if (!localStorage.getItem("access_token")) {
      router.replace("/");
      return;
    }

    // Try to get session details first (resume case)
    api.sessions
      .get(sessionId)
      .then(async (session) => {
        if (session.status === "PAUSED" || session.status === "ACTIVE") {
          const r = await api.sessions.reconnect(sessionId);
          setToken(r.livekit_token);
        } else if (session.status === "COMPLETED" || session.status === "EXPIRED") {
          setEnded(true);
        }
        setRoomName(session.room_name);
      })
      .catch(async () => {
        // Session doesn't exist — create fresh
        try {
          const s = await api.sessions.create();
          setToken(s.livekit_token);
          setRoomName(s.room_name);
          router.replace(`/session/${s.session_id}`);
        } catch (err: unknown) {
          setError(err instanceof Error ? err.message : "Failed to start session");
        }
      });
  }, [sessionId, router]);

  const handleDisconnected = useCallback(async () => {
    if (reconnectAttemptRef.current || ended) return;
    reconnectAttemptRef.current = true;
    try {
      const r = await api.sessions.reconnect(sessionId);
      setToken(r.livekit_token);
    } catch (err: unknown) {
      const e = err as { status?: number };
      if (e.status === 409) {
        setError("Session expired. Please start a new session.");
      }
    } finally {
      reconnectAttemptRef.current = false;
    }
  }, [sessionId, ended]);

  async function endSession() {
    try {
      await api.sessions.end(sessionId);
      setEnded(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to end session");
    }
  }

  if (error) {
    return (
      <main style={{ padding: 32 }}>
        <div role="alert" style={{ color: "#dc2626", padding: "12px 16px", background: "#fef2f2", borderRadius: 8 }}>
          {error}
        </div>
        <button onClick={() => router.push("/dashboard")} style={{ marginTop: 16, padding: "8px 16px" }}>
          Back to Dashboard
        </button>
      </main>
    );
  }

  if (ended) {
    return (
      <main style={{ maxWidth: 640, margin: "0 auto", padding: 32 }}>
        <h1>Session Complete</h1>
        <SessionSummary sessionId={sessionId} />
        <button onClick={() => router.push("/dashboard")} style={{ marginTop: 24, padding: "10px 20px", background: "#6366f1", color: "#fff", border: "none", borderRadius: 8, cursor: "pointer" }}>
          Back to Dashboard
        </button>
      </main>
    );
  }

  if (!token) {
    return <main style={{ padding: 32 }}>Connecting…</main>;
  }

  return (
    <LiveKitRoom
      token={token}
      serverUrl={LIVEKIT_URL}
      connect
      audio
      video={false}
      onDisconnected={handleDisconnected}
    >
      <RoomAudioRenderer />
      <main style={{ maxWidth: 640, margin: "0 auto", padding: 32 }}>
        <h1 style={{ marginBottom: 24 }}>Session with Alex</h1>
        <SessionControls onEnd={endSession} roomName={roomName} />
      </main>
    </LiveKitRoom>
  );
}
