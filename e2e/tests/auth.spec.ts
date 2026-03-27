import { test, expect } from "@playwright/test";
import { registerAndLogin } from "../helpers/auth";

const unique = () => `user_${Date.now()}@example.com`;

test("register with valid credentials redirects to dashboard", async ({ page }) => {
  await registerAndLogin(page, unique(), "StrongPass123!");
  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible();
});

test("register with duplicate email shows error", async ({ page }) => {
  const email = unique();
  await registerAndLogin(page, email, "StrongPass123!");
  await page.goto("/");
  await page.getByRole("tab", { name: "Register" }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("StrongPass123!");
  await page.getByRole("button", { name: "Register" }).click();

  await expect(page.getByRole("alert")).toContainText(/already registered/i);
});

test("login with wrong password shows error", async ({ page }) => {
  const email = unique();
  await registerAndLogin(page, email, "StrongPass123!");
  await page.goto("/");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("WrongPassword!");
  await page.getByRole("button", { name: "Login" }).click();

  await expect(page.getByRole("alert")).toContainText(/invalid credentials/i);
  await expect(page).not.toHaveURL(/\/dashboard/);
});

test("unauthenticated access to dashboard redirects to login", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\//);
  await expect(page.getByRole("button", { name: "Login" })).toBeVisible();
});

test("JWT is stored in localStorage after login", async ({ page }) => {
  await registerAndLogin(page, unique(), "StrongPass123!");
  const token = await page.evaluate(() => localStorage.getItem("access_token"));
  expect(token).toBeTruthy();
  expect(token!.split(".")).toHaveLength(3); // JWT has 3 parts
});
