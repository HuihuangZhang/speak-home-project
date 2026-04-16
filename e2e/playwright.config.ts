/// <reference types="node" />
import { defineConfig, devices } from "@playwright/test";
import * as dotenv from "dotenv";
dotenv.config({ path: "../.env" });

export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  retries: 2,
  workers: 1,
  use: {
    baseURL: process.env.FRONTEND_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
    video: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  // Start backend + frontend before running tests
  webServer: [
    {
      command: "bash ./scripts/start-backend.sh",
      cwd: ".",
      port: 8000,
      reuseExistingServer: false,
      env: {
        ...process.env,
        DATABASE_URL:
          process.env.DATABASE_URL ?? "sqlite+aiosqlite:////tmp/speakhome_e2e.db",
        LIVEKIT_URL: process.env.LIVEKIT_URL ?? "",
        LIVEKIT_API_URL: process.env.LIVEKIT_API_URL ?? "",
        LIVEKIT_API_KEY: process.env.LIVEKIT_API_KEY ?? "",
        LIVEKIT_API_SECRET: process.env.LIVEKIT_API_SECRET ?? "",
        DEEPGRAM_API_KEY: process.env.DEEPGRAM_API_KEY ?? "",
        OPENAI_API_KEY: process.env.OPENAI_API_KEY ?? "",
        JWT_SECRET: process.env.JWT_SECRET ?? "testsecret",
        JWT_EXPIRE_HOURS: process.env.JWT_EXPIRE_HOURS ?? "24",
        SESSION_PAUSE_TIMEOUT_MINUTES: process.env.SESSION_PAUSE_TIMEOUT_MINUTES ?? "5",
      },
    },
    {
      command: "npm run dev",
      cwd: "../frontend",
      port: 3000,
      reuseExistingServer: false,
      env: {
        NEXT_PUBLIC_API_URL: "http://localhost:8000",
        NEXT_PUBLIC_LIVEKIT_URL: process.env.LIVEKIT_URL ?? "",
      },
    },
  ],
});
