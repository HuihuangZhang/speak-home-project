import { test, expect } from "@playwright/test";
import { registerAndLogin } from "../helpers/auth";

const unique = () => `user_${Date.now()}_${Math.random().toString(36).slice(2, 8)}@example.com`;

test("Summary card appears after ending session", async ({ browser }) => {
  const page = await browser.newPage();
  await registerAndLogin(page, unique(), "StrongPass123!");

  // Start session
  await page.getByRole("button", { name: /start new session/i }).click();
  await page.waitForURL(/\/session\/(\d+)/);

  // Wait for connection
  await expect(page.getByTestId("connection-status")).toContainText(/connected|active/i, {
    timeout: 30_000,
  });

  // End the session
  await page.getByRole("button", { name: /end session/i }).click();
  // Confirm dialog if any
  const confirmBtn = page.getByRole("button", { name: /confirm|yes, end/i });
  if (await confirmBtn.isVisible()) await confirmBtn.click();

  // Summary card should appear (poll until done, up to 30s)
  await expect(page.getByTestId("summary-card")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("summary-exercises")).toBeVisible();
  await expect(page.getByTestId("summary-coaching-notes")).toBeVisible();
  await expect(page.getByTestId("summary-recommendations")).toBeVisible();
});

test("Summary poll shows loading state then resolves", async ({ browser }) => {
  const page = await browser.newPage();
  await registerAndLogin(page, unique(), "StrongPass123!");

  await page.getByRole("button", { name: /start new session/i }).click();
  await page.waitForURL(/\/session\/(\d+)/);
  await expect(page.getByTestId("connection-status")).toContainText(/connected|active/i, {
    timeout: 30_000,
  });

  await page.getByRole("button", { name: /end session/i }).click();

  // Loading indicator should be visible immediately after ending
  await expect(page.getByTestId("summary-loading")).toBeVisible({ timeout: 5_000 });
  // Then it should resolve into the actual summary
  await expect(page.getByTestId("summary-card")).toBeVisible({ timeout: 30_000 });
});

test("Dashboard session card shows summary preview after session ends", async ({ browser }) => {
  const page = await browser.newPage();
  await registerAndLogin(page, unique(), "StrongPass123!");

  await page.getByRole("button", { name: /start new session/i }).click();
  await page.waitForURL(/\/session\/(\d+)/);
  const sessionId = page.url().match(/\/session\/(\d+)/)![1];

  await expect(page.getByTestId("connection-status")).toContainText(/connected|active/i, {
    timeout: 30_000,
  });

  await page.getByRole("button", { name: /end session/i }).click();
  const confirmBtn = page.getByRole("button", { name: /confirm|yes, end/i });
  if (await confirmBtn.isVisible()) await confirmBtn.click();

  // Wait for summary to be generated
  await expect(page.getByTestId("summary-card")).toBeVisible({ timeout: 30_000 });

  // Go to dashboard and verify session card shows summary status
  await page.goto("/dashboard");
  const card = page.getByTestId(`session-card-${sessionId}`);
  await expect(card).toContainText(/completed/i);
  await expect(card).toContainText(/view summary/i);
});
