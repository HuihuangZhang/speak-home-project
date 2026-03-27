import { APIRequestContext } from "@playwright/test";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function forceExpireSession(
  request: APIRequestContext,
  token: string,
  sessionId: string
) {
  return request.post(`${API_URL}/test-utils/sessions/${sessionId}/force-expire`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}
