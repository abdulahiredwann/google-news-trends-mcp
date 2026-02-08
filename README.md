# Google News Trends — AI Chat Agent

A full-stack AI chat application that uses a ReAct agent (LangChain + OpenAI) with Google Trends/News tools and web search capabilities. Built with React, FastAPI, and Supabase.

**By Justin Rashidi, SeedX Inc**

---

## Features

- **AI Chat Agent** — ReAct agent powered by OpenAI GPT-4o-mini with tool-use reasoning
- **Google Trends & News** — 5 MCP tools for trending terms, news by keyword/location/topic, and top stories
- **Web Search** — Tavily integration for real-time web search
- **Real-time Streaming** — Server-Sent Events (SSE) for token-by-token response streaming
- **Chat History** — Persistent conversations stored in Supabase with per-user isolation (RLS)
- **Authentication** — Supabase Auth with JWT-based API protection
- **Dark/Light Mode** — Theme toggle with system preference detection
- **Dockerized** — One-command startup with Docker Compose (3 services)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4, shadcn/ui |
| Backend | Python 3.12, FastAPI, LangChain, LangGraph, OpenAI |
| Database | Supabase (PostgreSQL + Auth + RLS) |
| MCP Server | FastMCP, Playwright, Google News/Trends scraping |
| Tools | Tavily Search, Google Trends MCP (5 tools) |
| Deployment | Docker Compose (3 containers) |

---

## Project Structure

```
google-news-trends-mcp/
├── frontend/                  # React + TypeScript (Vite)
│   ├── src/
│   │   ├── api/               # API clients (auth, chat, SSE streaming)
│   │   ├── components/        # UI components (Sidebar, ThemeToggle, etc.)
│   │   ├── pages/             # LoginPage, SignupPage, ChatPage
│   │   ├── state/             # React context (AuthProvider, ThemeProvider)
│   │   └── types/             # TypeScript interfaces
│   ├── Dockerfile             # Multi-stage: Node build → Nginx serve
│   └── nginx.conf             # SPA routing config
│
├── backend/                   # FastAPI + LangChain
│   ├── app/
│   │   ├── core/              # Config (env vars via pydantic-settings)
│   │   ├── middleware/        # JWT auth middleware
│   │   ├── routers/           # API routes (auth, chat, health)
│   │   ├── schemas/           # Pydantic models
│   │   └── services/
│   │       ├── agent/         # ReAct agent (LangChain + LangGraph)
│   │       ├── db/            # Supabase client (messages CRUD)
│   │       └── tools/         # Tavily + Google Trends MCP adapters
│   └── Dockerfile             # Python 3.12 + uvicorn
│
├── mcp_server.py              # Google Trends MCP server (FastMCP)
├── tools.py                   # 5 MCP tool implementations
├── security/                  # MCP JWT verification
├── Dockerfile                 # MCP server (Python 3.12 + Playwright)
├── docker-compose.yml         # All 3 services orchestrated
├── DockerSetup.md             # Detailed Docker setup guide
└── TaskTracker.md             # Development task tracker
```

---

## Quick Start (Docker)

### Prerequisites

- Docker & Docker Compose (v2+)
- A [Supabase](https://supabase.com/) project
- An [OpenAI](https://platform.openai.com/) API key
- (Optional) A [Tavily](https://tavily.com/) API key

### 1. Clone and configure

```bash
git clone <your-repo-url>
cd google-news-trends-mcp

# Create env files from templates
cp .env.example .env
cp backend/.env.example backend/.env
```

### 2. Fill in your keys

**Root `.env`** — MCP JWT config (replace `YOUR_PROJECT` with your Supabase project ID):

```env
MCP_JWT_ISSUER=https://YOUR_PROJECT.supabase.co/auth/v1
MCP_JWT_JWKS_URL=https://YOUR_PROJECT.supabase.co/auth/v1/.well-known/jwks.json
MCP_JWT_AUDIENCE=authenticated
MCP_JWT_ALGORITHMS=ES256
```

**`backend/.env`** — API keys:

```env
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_KEY=your_supabase_anon_key
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
```

### 3. Set up Supabase database

Run this SQL in your Supabase SQL Editor:

```sql
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
  for select to authenticated using (user_id = auth.uid());

create policy "insert_own_messages" on public.messages
  for insert to authenticated with check (user_id = auth.uid());
```

> Also disable email confirmations in Supabase → Authentication → Settings for dev/testing.

### 4. Build and run

```bash
docker compose up --build -d
```

### 5. Open the app

Go to **http://localhost:3000** → Sign up → Log in → Chat!

> See [DockerSetup.md](DockerSetup.md) for detailed Docker documentation, troubleshooting, and architecture diagrams.

---

## Local Development (without Docker)

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Fill in your API keys
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # Starts on http://localhost:5173
```

### MCP Server (standalone)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install --with-deps chromium
uvicorn main:app --host 0.0.0.0 --port 8080
```

---

## MCP Tools

The Google Trends MCP server provides 5 tools:

| Tool | Description |
|------|-------------|
| **get_news_by_keyword** | Search for news using specific keywords |
| **get_news_by_location** | Retrieve news relevant to a particular location |
| **get_news_by_topic** | Get news based on a chosen topic |
| **get_top_news** | Fetch the top news stories from Google News |
| **get_trending_terms** | Return trending keywords from Google Trends for a location |

All news tools support article text summarization via LLM Sampling or NLP.

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/signup` | Create a new account |
| POST | `/auth/login` | Log in and get JWT token |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat/send` | Send a message, receive SSE stream |
| GET | `/chat/conversations` | List user's conversations |
| GET | `/chat/conversations/{id}/messages` | Get messages for a conversation |

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Backend health check |
| GET | `/healthz` | MCP server health check |

---

## How the ReAct Agent Works

The AI agent uses the **ReAct** (Reasoning + Acting) pattern via LangChain and LangGraph:

1. **User sends a message** → Backend loads chat history from Supabase
2. **Agent reasons** → Decides which tool(s) to use based on the query
3. **Agent acts** → Calls tools (Tavily search, Google Trends MCP, etc.)
4. **Agent observes** → Reads tool results, decides if more tools are needed
5. **Agent responds** → Generates a final answer, streamed token-by-token via SSE
6. **Messages saved** → Both user message and assistant response stored in Supabase

The agent has access to Tavily web search and 5 Google Trends/News tools, and autonomously decides which to use based on the user's question.

---

## MCP Server Authorization

Requests to `/mcp` require an `Authorization: Bearer <jwt>` header. The JWT is verified for:

- **Signature** — via JWKS endpoint (`MCP_JWT_JWKS_URL`)
- **Issuer** — must match `MCP_JWT_ISSUER`
- **Audience** — must match `MCP_JWT_AUDIENCE` (default: `authenticated`)
- **Algorithm** — Supabase uses `ES256`
- **Required claims** — `exp`, `aud`, `iss`

---

## Documentation

| Document | Description |
|----------|-------------|
| [DockerSetup.md](DockerSetup.md) | Detailed Docker setup, architecture, networking, troubleshooting |
| [TaskTracker.md](TaskTracker.md) | Development task tracker (83/83 tasks complete) |
