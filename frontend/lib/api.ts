const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init?.headers as Record<string, string> | undefined),
    },
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw Object.assign(new Error(err.detail ?? "Request failed"), {
      status: resp.status,
    });
  }
  if (resp.status === 202) return resp.json() as Promise<T>;
  return resp.json() as Promise<T>;
}

export const api = {
  auth: {
    register: (email: string, password: string) =>
      request<{ access_token: string; token_type: string }>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    login: (email: string, password: string) =>
      request<{ access_token: string; token_type: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
  },
  sessions: {
    create: () =>
      request<{ session_id: number; livekit_token: string; room_name: string }>(
        "/sessions",
        { method: "POST" }
      ),
    list: () =>
      request<{
        items: Array<{
          id: number;
          room_name: string;
          status: string;
          started_at: string | null;
          ended_at: string | null;
          duration_seconds: number;
        }>;
      }>("/sessions"),
    get: (id: number) =>
      request<{
        id: number;
        room_name: string;
        status: string;
        exercise_plan: unknown;
        duration_seconds: number;
      }>(`/sessions/${id}`),
    reconnect: (id: number) =>
      request<{ livekit_token: string; status: string }>(`/sessions/${id}/reconnect`, {
        method: "POST",
      }),
    end: (id: number) =>
      request<{ status: string }>(`/sessions/${id}/end`, { method: "POST" }),
  },
  summaries: {
    get: (sessionId: number) =>
      request<{
        status: string;
        exercises: unknown;
        coaching_notes: string | null;
        next_recommendations: string | null;
      }>(`/summaries/${sessionId}`),
  },
};
