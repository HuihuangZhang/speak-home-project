import { test, expect, Page } from "@playwright/test";
import { registerAndLogin } from "../helpers/auth";

const unique = () => `user_${Date.now()}@example.com`;

test.describe("Session flow", () => {
  let page: Page;
  let email: string;

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();
    email = unique();
    await registerAndLogin(page, email, "StrongPass123!");
  });

  test("Start New Session button creates a session and navigates to session page", async () => {
    await page.getByRole("button", { name: /start new session/i }).click();
    await page.waitForURL(/\/session\/\d+/);

    // Connection status indicator must be visible
    await expect(page.getByTestId("connection-status")).toBeVisible();
    // Mic toggle must be present
    await expect(page.getByRole("button", { name: /microphone|mic/i })).toBeVisible();
  });

  test("New session appears in dashboard history", async () => {
    await page.getByRole("button", { name: /start new session/i }).click();
    await page.waitForURL(/\/session\/\d+/);

    await page.goto("/dashboard");
    const sessionCards = page.getByTestId("session-card");
    await expect(sessionCards).toHaveCount(1);
  });

  test("Session page shows room name", async () => {
    await page.getByRole("button", { name: /start new session/i }).click();
    await page.waitForURL(/\/session\/\d+/);
    // Room name should be shown somewhere (e.g., in metadata or title)
    await expect(page.getByTestId("room-name")).toContainText(/session-/);
  });

  test("Session page shows ACTIVE status after connection", async () => {
    await page.getByRole("button", { name: /start new session/i }).click();
    await page.waitForURL(/\/session\/\d+/);

    // Poll until status is ACTIVE (agent has joined and connection is established)
    await expect(page.getByTestId("connection-status")).toContainText(/connected|active/i, {
      timeout: 30_000,
    });
  });
});
