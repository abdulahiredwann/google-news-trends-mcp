# 🐳 Docker Setup Guide

A step-by-step guide to configure and run the full application using Docker Compose.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed (v20+)
- [Docker Compose](https://docs.docker.com/compose/install/) installed (v2+)
- A [Supabase](https://supabase.com/) project (free tier works)
- An [OpenAI](https://platform.openai.com/) API key
- (Optional) A [Tavily](https://tavily.com/) API key for web search

---

## Step 1 — Clone the Repository

```bash
git clone <your-repo-url>
cd google-news-trends-mcp
```

---

## Step 2 — Set Up Supabase

Before configuring environment variables, you need a Supabase project with a `messages` table.

### 2a. Create a Supabase Project

Go to [supabase.com](https://supabase.com/), create a new project, and note down:
- **Project URL** — e.g. `https://abcdefgh.supabase.co`
- **Anon/Public Key** — found in Settings → API

### 2b. Create the Messages Table

In the Supabase SQL Editor, run:

```sql
create extension if not exists "pgcrypto";

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  conversation_id text not null,
  role text not null check (role in ('user','assistant','system')),
  content text not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_messages_user_conv_time
  on public.messages (user_id, conversation_id, created_at);

alter table public.messages enable row level security;

create policy "read_own_messages" on public.messages
  for select to authenticated
  using (user_id = auth.uid());

create policy "insert_own_messages" on public.messages
  for insert to authenticated
  with check (user_id = auth.uid());
```

### 2c. Disable Email Confirmation (for dev/testing)

In Supabase Dashboard → Authentication → Settings → turn off **"Enable email confirmations"** so signup works instantly without email verification.

---

## Step 3 — Configure Environment Variables

There are **2 `.env` files** you need to create. Templates are provided as `.env.example`.

### 3a. Root `.env` (MCP Server JWT Config)

```bash
cp .env.example .env
```

Edit `.env` and fill in your Supabase project ID:

```env
# Replace YOUR_PROJECT with your Supabase project ID
# (the subdomain part of your Supabase URL, e.g. "abcdefgh")

MCP_JWT_ISSUER=https://YOUR_PROJECT.supabase.co/auth/v1
MCP_JWT_JWKS_URL=https://YOUR_PROJECT.supabase.co/auth/v1/.well-known/jwks.json
MCP_JWT_AUDIENCE=authenticated
MCP_JWT_ALGORITHMS=ES256
```

> **What this does:** The MCP server uses these to verify that incoming requests have a valid Supabase JWT. The `ES256` algorithm matches Supabase's signing method.

### 3b. Backend `.env` (API Keys & Supabase)

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and fill in your keys:

```env
# Supabase (required)
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_KEY=your_supabase_anon_public_key

# OpenAI (required — powers the AI agent)
OPENAI_API_KEY=sk-...

# Tavily Web Search (optional — agent still works without it)
TAVILY_API_KEY=tvly-...

# These are for local development only.
# Docker Compose overrides them automatically.
MCP_SERVER_URL=http://localhost:8080/mcp/
FRONTEND_URL=http://localhost:5173
```

> **Note:** You do NOT need a `frontend/.env` file for Docker. The frontend's `VITE_API_URL` is set as a build argument in `docker-compose.yml` and baked into the JavaScript bundle at build time.

### Summary of env files:

| File | Purpose | Used By |
|------|---------|---------|
| `.env` (root) | MCP JWT verification config | `docker-compose.yml` → MCP server |
| `backend/.env` | Supabase, OpenAI, Tavily API keys | `docker-compose.yml` → Backend |

---

## Step 4 — Build and Start

One command builds all 3 Docker images and starts the services:

```bash
docker compose up --build -d
```

**What happens:**

1. **MCP Server** image builds (Python 3.12 + Playwright + Chromium) — takes ~2-3 min first time
2. **Backend** image builds (Python 3.12 + FastAPI dependencies) — takes ~1-2 min
3. **Frontend** image builds (Node 20 → Vite build → Nginx) — takes ~1 min
4. MCP server starts and passes health check
5. Backend starts (waits for MCP to be healthy first)
6. Frontend starts (waits for Backend to be healthy first)

> First build takes 5-10 minutes. Subsequent builds are much faster due to Docker layer caching.

---

## Step 5 — Verify Everything is Running

```bash
docker compose ps
```

You should see all 3 containers as **healthy** or **running**:

```
NAME                                           STATUS
google-news-trends-mcp-google-trends-mcp-1     Up (healthy)
google-news-trends-mcp-backend-1               Up (healthy)
google-news-trends-mcp-frontend-1              Up
```

Test the health endpoints:

```bash
curl http://localhost:8080/healthz   # → ok
curl http://localhost:8000/health    # → {"status":"ok"}
curl -s http://localhost:3000 | head -5  # → HTML page
```

---

## Step 6 — Use the App

Open **http://localhost:3000** in your browser.

1. **Sign up** — create an account with email + password
2. **Log in** — use your credentials
3. **Chat** — ask questions; the AI agent will use:
   - **Tavily** for web search (if API key provided)
   - **Google Trends MCP** for trending topics and news
   - **OpenAI GPT** for reasoning and responses

---

## How It Works

### Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    Docker Compose Network                       │
│                                                                │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ google-trends-  │  │     backend      │  │   frontend   │  │
│  │      mcp        │  │                  │  │              │  │
│  │                 │  │  FastAPI + AI    │  │  React +     │  │
│  │  MCP Server +   │◄─│  ReAct Agent    │  │  Nginx       │  │
│  │  Playwright     │  │                  │  │              │  │
│  │  Port: 8080     │  │  Port: 8000     │  │  Port: 80    │  │
│  └─────────────────┘  └───────┬──────────┘  └──────────────┘  │
│                               │                                │
│                       ┌───────▼────────┐                       │
│                       │   Supabase     │                       │
│                       │  (External)    │                       │
│                       │  Auth + DB     │                       │
│                       └────────────────┘                       │
└────────────────────────────────────────────────────────────────┘
```

### Port Mapping

| Service | Host Port | Container Port | URL |
|---------|-----------|----------------|-----|
| Frontend | 3000 | 80 (nginx) | http://localhost:3000 |
| Backend | 8000 | 8000 (uvicorn) | http://localhost:8000 |
| MCP Server | 8080 | 8080 (uvicorn) | http://localhost:8080 |

### How Services Talk to Each Other

- **Browser → Backend:** The React app (running in your browser) sends API requests to `http://localhost:8000` — the host-mapped port.
- **Backend → MCP:** Inside Docker, the backend calls `http://google-trends-mcp:8080/mcp/` using the Docker service name. Docker's internal DNS resolves this to the MCP container's IP.
- **Backend → Supabase:** Direct HTTPS to your Supabase project URL (external).
- **MCP JWT Auth:** The backend forwards the user's Supabase JWT token to the MCP server, which verifies it using the JWKS endpoint.

### Startup Order

Docker Compose health checks enforce the startup order:

```
1. google-trends-mcp starts → GET /healthz returns 200
2. backend starts (depends on MCP healthy) → GET /health returns 200
3. frontend starts (depends on backend healthy) → Nginx serves on port 80
```

---

## Common Commands

```bash
# Start all services (detached)
docker compose up -d

# Rebuild and start (after code changes)
docker compose up --build -d

# View logs (all services)
docker compose logs -f

# View logs (one service)
docker compose logs -f backend

# Stop all services
docker compose down

# Stop and remove everything (images, volumes)
docker compose down --rmi all --volumes

# Restart a single service
docker compose restart backend

# Check service status
docker compose ps
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `resolution-too-deep` during build | Loose Python dependency versions | Versions are already pinned in `requirements.txt` — just rebuild |
| MCP returns `500 Internal Server Error` | JWT env vars not set | Check root `.env` has `MCP_JWT_ISSUER` and `MCP_JWT_JWKS_URL` |
| MCP returns `Invalid MCP JWT` | Wrong algorithm | Supabase uses `ES256` — ensure `MCP_JWT_ALGORITHMS=ES256` in root `.env` |
| `307 Temporary Redirect` from MCP | Missing trailing slash | Backend uses `http://google-trends-mcp:8080/mcp/` (with trailing `/`) |
| Frontend blank white page | Wrong backend URL | Check `VITE_API_URL` build arg in `docker-compose.yml` |
| Backend can't reach MCP | Service not healthy yet | Check `docker compose ps` — wait for MCP to show "healthy" |
| CORS errors in browser | Backend CORS config | `FRONTEND_URL` in `backend/.env` must match the frontend URL |
| Login/signup fails | Supabase email confirmation on | Disable email confirmations in Supabase dashboard |

---

## Files Overview

| File | What It Does |
|------|-------------|
| `docker-compose.yml` | Defines all 3 services, ports, env vars, health checks, startup order |
| `Dockerfile` (root) | Builds MCP server image (Python 3.12 + Playwright + Chromium) |
| `backend/Dockerfile` | Builds backend image (Python 3.12 + FastAPI + uvicorn) |
| `frontend/Dockerfile` | Builds frontend image (Node 20 build → Nginx serve) |
| `frontend/nginx.conf` | Nginx config: SPA routing, static asset caching |
| `.env.example` | Template for root env vars (MCP JWT config) |
| `backend/.env.example` | Template for backend env vars (API keys) |
| `frontend/.env.example` | Template for frontend env vars (backend URL) |
| `.gitignore` | Ensures `.env` files with secrets are never committed |
