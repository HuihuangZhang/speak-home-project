import { expect, Page } from "@playwright/test";

export async function registerAndLogin(
  page: Page,
  email: string,
  password: string
): Promise<void> {
  await page.goto("/");
  await page.getByRole("tab", { name: "Register" }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Register" }).click();
  // Next.js client navigation may not trigger a full "load" event; assert URL directly.
  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 30_000 });
  await page.waitForFunction(() => !!localStorage.getItem("access_token"), null, {
    timeout: 10_000,
  });
}

export async function login(
  page: Page,
  email: string,
  password: string
): Promise<void> {
  await page.goto("/");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 30_000 });
  await page.waitForFunction(() => !!localStorage.getItem("access_token"), null, {
    timeout: 10_000,
  });
}
