"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { formatDurationSeconds } from "@/lib/formatDuration";

interface SessionItem {
  id: number;
  room_name: string;
  status: string;
  started_at: string | null;
  duration_seconds: number;
}

export default function DashboardPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!localStorage.getItem("access_token")) {
      router.replace("/");
      return;
    }
    api.sessions
      .list()
      .then((res) => setSessions(res.items))
      .catch(() => setError("Failed to load sessions"))
      .finally(() => setLoading(false));
  }, [router]);

  async function startNew() {
    try {
      const session = await api.sessions.create();
      router.push(`/session/${session.session_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start session");
    }
  }

  async function resume(sessionId: number, sessionStatus: string) {
    // For paused sessions, verify reconnect is still valid before navigating
    if (sessionStatus === "PAUSED") {
      try {
        await api.sessions.reconnect(sessionId);
      } catch (err: unknown) {
        const e = err as { status?: number };
        if (e.status === 409) {
          setError("Session expired. Please start a new session.");
          return;
        }
        setError(err instanceof Error ? err.message : "Failed to resume session");
        return;
      }
    }
    router.push(`/session/${sessionId}`);
  }

  if (loading) return <main style={{ padding: 32 }}>Loading…</main>;

  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: 32 }}>
      <h1>Dashboard</h1>
      {error && <div role="alert" style={{ color: "#dc2626", marginBottom: 16 }}>{error}</div>}

      <button
        onClick={startNew}
        style={{ padding: "12px 24px", background: "#6366f1", color: "#fff", border: "none", borderRadius: 8, fontSize: 16, cursor: "pointer", marginBottom: 32 }}
      >
        Start New Session
      </button>

      {sessions.length === 0 ? (
        <p style={{ color: "#6b7280" }}>No sessions yet. Start your first workout!</p>
      ) : (
        <div>
          {sessions.map((s) => (
            <div
              key={s.id}
              data-testid="session-card"
              data-session-id={s.id}
              style={{ background: "#fff", borderRadius: 12, padding: 20, marginBottom: 16, boxShadow: "0 1px 4px #0001", display: "flex", justifyContent: "space-between", alignItems: "center" }}
            >
              <div data-testid={`session-card-${s.id}`}>
                <p style={{ margin: 0, fontWeight: 600 }}>{s.room_name}</p>
                <p style={{ margin: "4px 0 0", fontSize: 13, color: "#6b7280", textTransform: "capitalize" }}>{s.status.toLowerCase()}</p>
                <p style={{ margin: "4px 0 0", fontSize: 13, color: "#4b5563" }} data-testid="session-duration">
                  Active time: {formatDurationSeconds(s.duration_seconds)}
                </p>
                {s.status === "COMPLETED" && (
                  <a href={`/session/${s.id}?summary=1`} style={{ fontSize: 13, color: "#6366f1" }}>View Summary</a>
                )}
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                {(s.status === "PAUSED" || s.status === "ACTIVE") && (
                  <button
                    onClick={() => resume(s.id, s.status)}
                    style={{ padding: "8px 16px", background: "#10b981", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}
                  >
                    Resume
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
