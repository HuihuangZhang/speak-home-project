# ── Stage 1: install dependencies ────────────────────────────────────────────
FROM node:22.21.1-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --prefer-offline

# ── Stage 2: build Next.js application ───────────────────────────────────────
FROM node:22.21.1-alpine AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* variables are baked into the client-side JS bundle at build
# time.  Pass them as build args in docker-compose (or `docker build --build-arg`).
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_LIVEKIT_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_LIVEKIT_URL=$NEXT_PUBLIC_LIVEKIT_URL

RUN npm run build

# ── Stage 3: minimal production runner ───────────────────────────────────────
# `output: "standalone"` (next.config.js) produces .next/standalone which
# includes only the node_modules actually needed at runtime — no full install.
FROM node:22.21.1-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# Standalone server bundle
COPY --from=builder /app/.next/standalone ./
# Static assets must be placed at .next/static inside the working directory
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
