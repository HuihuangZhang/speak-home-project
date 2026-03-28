/** @type {import('next').NextConfig} */
const fs = require("fs");
const path = require("path");

// Load root .env so frontend can access shared vars like LIVEKIT_URL
function loadRootEnv() {
  const rootEnv = path.resolve(__dirname, "../.env");
  try {
    const lines = fs.readFileSync(rootEnv, "utf8").split("\n");
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const eq = trimmed.indexOf("=");
      if (eq === -1) continue;
      const key = trimmed.slice(0, eq).trim();
      const val = trimmed.slice(eq + 1).trim();
      if (!process.env[key]) process.env[key] = val;
    }
  } catch {
    // no root .env — ignore
  }
}

loadRootEnv();

const nextConfig = {
  // Produces a self-contained bundle in .next/standalone — used by the Docker image.
  // Has no effect on `next dev` or a regular `next build` outside Docker.
  output: "standalone",
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    NEXT_PUBLIC_LIVEKIT_URL: process.env.NEXT_PUBLIC_LIVEKIT_URL || process.env.LIVEKIT_URL || "",
  },
};

module.exports = nextConfig;
