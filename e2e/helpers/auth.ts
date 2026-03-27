import { Page } from "@playwright/test";

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
  // After register, should redirect to dashboard
  await page.waitForURL("**/dashboard");
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
  await page.waitForURL("**/dashboard");
}
