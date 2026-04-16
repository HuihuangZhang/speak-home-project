import { test, expect } from "@playwright/test";
import { registerAndLogin } from "../helpers/auth";

const unique = () => `user_${Date.now()}@example.com`;

test("Reconnect: navigating away and back within 5 minutes resumes session", async ({
  browser,
}) => {
  const page = await browser.newPage();
  const email = unique();
  await registerAndLogin(page, email, "StrongPass123!");

  // Start a session
  await page.getByRole("button", { name: /start new session/i }).click();
  await page.waitForURL(/\/session\/(\d+)/);
  const sessionUrl = page.url();
  const sessionId = sessionUrl.match(/\/session\/(\d+)/)![1];

  // Wait for actual LiveKit connection (not "Disconnected" or "Connecting")
  await expect(page.getByTestId("connection-status")).toHaveText(/^connected$/i, {
    timeout: 30_000,
  });

  // Navigate away (simulates tab close / navigation)
  await page.goto("/dashboard");

  // Find the outer session card that contains this session's info div,
  // then check for the Resume button inside the same outer card.
  const sessionCard = page
    .getByTestId("session-card")
    .filter({ has: page.getByTestId(`session-card-${sessionId}`) });
  await expect(sessionCard).toBeVisible();
  await expect(sessionCard.getByRole("button", { name: /resume/i })).toBeVisible();

  // Click Resume
  await sessionCard.getByRole("button", { name: /resume/i }).click();
  await page.waitForURL(`**/session/${sessionId}`);

  // Must reconnect to the SAME session (not a new one)
  await expect(page.getByTestId("room-name")).toContainText(`session-${sessionId}`);
  await expect(page.getByTestId("connection-status")).toHaveText(/^connected$/i, {
    timeout: 30_000,
  });
});

test("Reconnect: expired session (>5 min) shows error and Start New prompt", async ({
  browser,
  request,
}) => {
  const page = await browser.newPage();
  const email = unique();
  await registerAndLogin(page, email, "StrongPass123!");

  // Start a session
  await page.getByRole("button", { name: /start new session/i }).click();
  await page.waitForURL(/\/session\/(\d+)/);
  const sessionId = page.url().match(/\/session\/(\d+)/)![1];

  // Force-expire the session via API (set paused_at to 10 min ago)
  const token = await page.evaluate(() => localStorage.getItem("access_token"));
  await request.post(`http://localhost:8000/sessions/${sessionId}/force-expire`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  // Navigate to dashboard and try to resume
  await page.goto("/dashboard");
  const sessionCard = page
    .getByTestId("session-card")
    .filter({ has: page.getByTestId(`session-card-${sessionId}`) });
  await sessionCard.getByRole("button", { name: /resume/i }).click();

  // Should show error, not navigate to session
  await expect(
    page.getByRole("alert").filter({ hasText: /session expired|start a new session/i })
  ).toBeVisible();
});
