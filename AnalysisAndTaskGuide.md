# 🔍 Complete Project Analysis & Task Guide

## Based on TestDocumentation.md Requirements

---

## 📂 1. CURRENT FOLDER STRUCTURE (What Already Exists)

```
google-news-trends-mcp/
├── auth.py                    # Simple UnauthorizedError class + check_authorization helper
├── Dockerfile                 # Docker image for the MCP server only
├── LICENSE
├── load_var.py                # Loads JWT environment variables (audience, issuer, JWKS, etc.)
├── main.py                    # FastAPI app → mounts MCP server at /mcp + /healthz endpoint
├── mcp_server.py              # FastMCP server with AuthorizationMiddleware + tool registration
├── pyproject.toml             # Python dependencies & project metadata
├── README.md                  # Existing documentation for the MCP server
├── security/
│   ├── __init__.py            # Exports: get_request_auth, verify_mcp_jwt
│   ├── utils.py               # Header extraction, PEM normalization, bearer token parsing
│   └── verification.py        # JWT decode + claim validation (issuer, audience, scope)
├── TestDocumentation.md       # The test/requirement document
└── tools.py                   # ALL MCP tools: news by keyword/location/topic, top news, trending terms
```

---

## 📂 2. REQUIRED FOLDER STRUCTURE (What Test Expects)

```
project-root/
├── frontend/                       ❌ DOES NOT EXIST — Must Build
│   ├── src/
│   │   ├── api/                    # API client functions (login, chat, etc.)
│   │   ├── components/             # React components (ChatBox, MessageBubble, ToolIndicator, etc.)
│   │   ├── pages/                  # Pages (LoginPage, ChatPage)
│   │   ├── state/                  # State management (AuthContext, ChatContext)
│   │   ├── types/                  # TypeScript type definitions
│   │   └── utils/                  # Utility functions
│   ├── Dockerfile                  # Frontend Docker image
│   ├── package.json
│   └── .env.example
│
├── backend/                        ❌ DOES NOT EXIST — Must Build
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── core/                   # Config, settings
│   │   ├── middleware/             # Auth middleware (token validation)
│   │   ├── routers/
│   │   │   ├── auth.py             # Signup + Login endpoints
│   │   │   ├── chat.py             # Streaming chat endpoint (SSE)
│   │   │   └── health.py           # Health check endpoint
│   │   ├── schemas/                # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── agent/              # LangChain ReAct agent logic
│   │   │   ├── tools/
│   │   │   │   ├── tavily.py       # Tavily web search tool
│   │   │   │   └── google_trends_mcp.py  # MCP adapter to connect to the existing MCP server
│   │   │   └── db/                 # Supabase integration (chat memory, user queries)
│   │   └── utils/                  # Helpers, logging
│   ├── Dockerfile                  # Backend Docker image
│   ├── requirements.txt
│   └── .env.example
│
├── docker-compose.yml              ❌ DOES NOT EXIST — Must Build
├── README.md                       ✅ EXISTS (may need updating)
├── .env.example                    ❌ DOES NOT EXIST — Must Create
│
└── google-news-trends-mcp/         ✅ EXISTS — This is the MCP server (already done)
    ├── main.py
    ├── mcp_server.py
    ├── tools.py
    ├── auth.py
    ├── load_var.py
    ├── Dockerfile
    ├── security/
    │   ├── __init__.py
    │   ├── utils.py
    │   └── verification.py
    └── pyproject.toml
```

---

## 📄 3. FILE-BY-FILE ANALYSIS (Existing Code)

### `main.py` — FastAPI Entry Point for MCP Server
```
- Creates FastAPI app
- Mounts the MCP HTTP app at "/mcp"
- Exposes /healthz endpoint → returns "ok"
- This is the MCP server's entry point, NOT the backend's
```
**Role in the test:** This is the Google Trends MCP container. The backend will CONNECT to this via Docker networking.

---

### `mcp_server.py` — MCP Server Setup + Auth Middleware
```
- Creates FastMCP instance named "google-news-trends"
- AuthorizationMiddleware → calls verify_mcp_jwt() on every request
- If JWT invalid → returns 401 JSON error
- Uses BrowserManager lifespan for Playwright browser
- Registers all tools from tools.py
```
**Role in the test:** This is the middleware that protects the MCP tools. The backend must send valid JWT tokens when calling MCP tools.

---

### `tools.py` — All MCP Tools (577 lines)
```
Core tools registered:
1. get_news_by_keyword    → Search news by keyword
2. get_news_by_location   → News by location (city/state/country)
3. get_news_by_topic      → News by topic (TECHNOLOGY, SPORTS, etc.)
4. get_top_news           → Top stories from Google News
5. get_trending_terms     → Google Trends data by geo (US, GB, etc.)

Support classes:
- ArticleOut              → Pydantic model for article output
- TrendingTermOut         → Pydantic model for trend output
- BrowserManager          → Manages Playwright headless browser
- Uses: gnews, newspaper4k, trendspy, cloudscraper, playwright
```
**Role in the test:** These are the MCP tools the ReAct agent will call via the LangChain MCP Adapter. Specifically TOOL-02 tests.

---

### `auth.py` — Simple Authorization Check
```
- UnauthorizedError exception class
- check_authorization() → Checks for "Bearer" in Authorization header
```
**Role in the test:** Basic auth check, but the FULL auth (signup/login with Supabase) must be built in the backend.

---

### `load_var.py` — Environment Variable Loader
```
- Loads JWT-related env vars:
  MCP_JWT_AUDIENCE, MCP_JWT_ISSUER, MCP_JWT_JWKS_URL,
  MCP_JWT_PUBLIC_KEY, MCP_JWT_REQUIRED_SCOPE, MCP_JWT_ALGORITHMS
- Uses python-dotenv
```
**Role in the test:** Configures JWT verification for the MCP server.

---

### `security/utils.py` — Security Utilities
```
- _extract_header_value()   → Get header from various header formats
- normalize_pem()           → Clean PEM public key strings
- _get_headers_from_ctx()   → Extract headers from FastMCP Context
- _get_bearer_token()       → Parse "Bearer <token>" from Authorization header
- get_request_auth()        → Get XGAAccessToken + XGTeamID from headers
```
**Role in the test:** Support functions for JWT verification.

---

### `security/verification.py` — JWT Verification
```
- _get_jwt_signing_key()    → Gets key from JWKS URL or public PEM
  NOTE: This function is DUPLICATED (defined twice) — possible bug
- verify_mcp_jwt()          → Full JWT verification:
  - Checks issuer is configured
  - Extracts bearer token
  - Decodes JWT with signature, audience, issuer validation
  - Checks required scope if configured
```
**Role in the test:** This is what protects the MCP server from unauthorized access.

---

### `Dockerfile` — MCP Server Docker Image
```
- Python 3.11-slim base
- Installs via pip install .
- Runs: uvicorn main:app --host 0.0.0.0 --port 8080
```
**Role in the test:** The MCP server container. Docker Compose will reference this.

---

### `pyproject.toml` — Dependencies
```
Key dependencies:
- fastmcp >= 2.9.2          (MCP server framework)
- fastapi >= 0.111.0        (HTTP server)
- gnews >= 0.4.1            (Google News RSS)
- newspaper4k >= 0.9.3.1    (Article parsing)
- trendspy >= 0.1.6         (Google Trends)
- playwright >= 1.53.0      (Headless browser)
- PyJWT >= 2.8.0            (JWT verification)
- cloudscraper >= 1.2.71    (Anti-bot scraping)
```

---

## ✅ 4. WHAT ALREADY EXISTS (You Don't Need to Build)

| Component | Status | Details |
|-----------|--------|---------|
| Google Trends MCP Server | ✅ Done | `main.py`, `mcp_server.py`, `tools.py` |
| MCP Tools (5 tools) | ✅ Done | News by keyword/location/topic, top news, trending terms |
| MCP JWT Authentication | ✅ Done | `security/verification.py` |
| MCP Dockerfile | ✅ Done | `Dockerfile` |
| MCP Health Check | ✅ Done | `/healthz` endpoint |

---

## ❌ 5. WHAT YOU MUST BUILD (Task List)

### 🔴 A. Frontend (React + TypeScript)

| Task | Priority | Details |
|------|----------|---------|
| Login Page | HIGH | Email + password form → calls backend auth API |
| Signup Page | HIGH | Registration form → creates Supabase user |
| Chat Page | HIGH | Main chat UI with streaming message display |
| SSE Streaming | HIGH | Connect to backend SSE endpoint, render tokens incrementally |
| Tool Activity Indicators | HIGH | Show "Searching web…", "Fetching trends…" during tool calls |
| Auth State Management | HIGH | Store JWT token, redirect on auth failure |
| Chat History Display | MEDIUM | Load previous messages from Supabase on page load |
| Reconnect Safety | MEDIUM | Handle page refresh without duplicating messages |
| Dockerfile | HIGH | Containerize the React app |
| .env.example | LOW | Document required env vars |

### 🔴 B. Backend (FastAPI)

| Task | Priority | Details |
|------|----------|---------|
| FastAPI app (`main.py`) | HIGH | Entry point with CORS, middleware |
| Auth Router (`routers/auth.py`) | HIGH | Signup + Login endpoints using Supabase |
| Chat Router (`routers/chat.py`) | HIGH | SSE streaming endpoint |
| Health Router (`routers/health.py`) | LOW | `/health` → OK |
| Auth Middleware | HIGH | Validate Supabase JWT on every chat request |
| LangChain ReAct Agent | HIGH | Agent that picks between tools based on prompt |
| Tavily Tool (`tools/tavily.py`) | HIGH | Tavily web search integration |
| MCP Adapter (`tools/google_trends_mcp.py`) | HIGH | Connect to MCP server via LangChain MCP adapter |
| Supabase DB Service (`services/db/`) | HIGH | Save/load chat messages, user isolation |
| Chat Memory Service | HIGH | Load conversation history into agent context |
| Schemas | MEDIUM | Pydantic models for API requests/responses |
| Dockerfile | HIGH | Containerize the backend |
| requirements.txt | HIGH | All Python dependencies |
| .env.example | LOW | Document required env vars |

### 🔴 C. Infrastructure

| Task | Priority | Details |
|------|----------|---------|
| docker-compose.yml | HIGH | Orchestrate frontend + backend + MCP server |
| Supabase Tables | HIGH | Create messages table with RLS policies |
| Supabase RLS Policies | HIGH | Users can only see their own messages |
| Docker Networking | HIGH | Backend connects to MCP via service name (NOT localhost) |
| Root .env.example | MEDIUM | All env vars needed for the full system |

---

## 🧠 6. KEY CONCEPTS YOU MUST UNDERSTAND

### 6.1 — SSE (Server-Sent Events) vs WebSocket

**What to know:**
- SSE = one-way streaming from server to client over HTTP
- WebSocket = bi-directional persistent connection
- **Why SSE for this project:** Chat responses flow one way (server → client). SSE is simpler, works through proxies/load balancers, auto-reconnects, and uses standard HTTP. No need for bidirectional communication since user sends a prompt via POST and receives streamed response via SSE.

**Interview answer:**
> "We chose SSE because our streaming is unidirectional — the server streams tokens to the client. SSE is simpler than WebSocket, works over standard HTTP, supports auto-reconnection, and doesn't require a persistent bidirectional connection. The user's prompt is sent via a regular POST request, and the response streams back via SSE."

---

### 6.2 — How the ReAct Agent Decides Between Tools

**What to know:**
- ReAct = Reasoning + Acting. The LLM reasons about which tool to use, acts (calls the tool), observes the result, then reasons again.
- LangChain's `create_react_agent` gives the LLM descriptions of all available tools.
- The LLM reads the user's prompt and tool descriptions, then decides:
  - "Search the web for LangChain" → **Tavily** (web search tool)
  - "Check Google Trends for AI agents" → **Google Trends MCP** (trends data)
  - "What is SSE streaming?" → **No tool** (LLM can answer from its own knowledge)

**Interview answer:**
> "The ReAct agent receives tool descriptions at initialization. When a user prompt comes in, the LLM reasons about which tool best answers the question. If the prompt asks about web search results, it picks Tavily. If it asks about trending keywords or Google News, it picks the MCP tools. If it can answer from training data, it uses no tool. The agent loops: Thought → Action → Observation → Thought until it has a final answer."

---

### 6.3 — How the MCP Adapter is Wired

**What to know:**
- The MCP server runs in its own Docker container (the existing code)
- The backend uses `langchain-mcp-adapters` to connect to it
- Connection flow:
  ```
  Backend → HTTP POST to http://google-trends-mcp:8080/mcp → MCP Server → Runs tool → Returns result
  ```
- The adapter converts MCP tools into LangChain-compatible tools
- JWT token must be sent with every MCP request

**Interview answer:**
> "The backend uses the LangChain MCP Adapter (`MultiServerMCPClient`) to connect to the MCP server over HTTP. The MCP server runs in a separate Docker container. The adapter discovers available tools via the MCP protocol and wraps them as LangChain tools. When the ReAct agent decides to use a Google Trends/News tool, the adapter sends an HTTP request with the JWT to the MCP server at `http://google-trends-mcp:8080/mcp`."

---

### 6.4 — How Supabase RLS Prevents Data Leaks

**What to know:**
- RLS = Row Level Security. Supabase/Postgres feature.
- Each row in the messages table has a `user_id` column
- RLS policy: `auth.uid() = user_id` — users can ONLY read/write their own rows
- Even if someone crafts a raw SQL query, Postgres enforces the policy

**Required SQL:**
```sql
-- Enable RLS
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own messages
CREATE POLICY "Users can view own messages" ON messages
  FOR SELECT USING (auth.uid() = user_id);

-- Policy: Users can only insert their own messages
CREATE POLICY "Users can insert own messages" ON messages
  FOR INSERT WITH CHECK (auth.uid() = user_id);
```

**Interview answer:**
> "Supabase uses Postgres Row Level Security. We enable RLS on the messages table and create policies that compare `auth.uid()` (the authenticated user's ID from the JWT) with the `user_id` column. This means even if User B somehow gets the query for User A's messages, Postgres itself blocks the data. It's enforced at the database level, not the application level."

---

### 6.5 — How Chat Memory is Loaded into the Agent

**What to know:**
- On each new user message, the backend:
  1. Loads previous messages from Supabase for this `conversation_id`
  2. Converts them to LangChain message format (`HumanMessage`, `AIMessage`)
  3. Passes them as the conversation history to the ReAct agent
  4. After agent responds, saves both user message and agent response to Supabase
- This gives the agent "memory" of the conversation

**Interview answer:**
> "When a user sends a message, the backend fetches all previous messages for that conversation from Supabase, ordered by timestamp. These are converted to LangChain HumanMessage and AIMessage objects and passed to the agent as conversation history. After the agent responds, both the user's message and the agent's response are saved to Supabase. This way the agent has full context of the conversation."

---

### 6.6 — How Middleware Blocks Unknown Access

**What to know:**
- The backend has middleware that runs BEFORE any chat endpoint
- It extracts the `Authorization: Bearer <token>` header
- It verifies the token with Supabase (checks signature, expiry, etc.)
- If invalid → returns 401/403 immediately, request never reaches the endpoint
- No token = no access. Invalid token = no access. Expired token = no access.

**Interview answer:**
> "We use FastAPI middleware that intercepts every request to protected endpoints. It extracts the Bearer token from the Authorization header and verifies it against Supabase's JWT secret. If the token is missing, invalid, or expired, the middleware returns a 401 response immediately — the request never reaches the route handler. This protects all chat and data endpoints."

---

### 6.7 — Docker Networking Decisions

**What to know:**
- All services are on the same Docker Compose network
- Services reference each other by **service name** (e.g., `http://google-trends-mcp:8080`), NOT `localhost`
- Frontend → Backend: via exposed port (e.g., `http://backend:8000`)
- Backend → MCP: via Docker network (e.g., `http://google-trends-mcp:8080/mcp`)
- Only frontend port is exposed to the host machine
- Backend and MCP communicate internally

**Interview answer:**
> "Docker Compose creates a default bridge network. All services communicate via service names, never localhost. The backend calls the MCP server at `http://google-trends-mcp:8080/mcp`. Only the frontend's port is exposed externally. The backend and MCP server communicate only on the internal Docker network, reducing attack surface."

---

### 6.8 — Failure Handling Strategy

**What to know:**
- If MCP server is down → agent should return friendly error, NOT crash
- If Tavily API fails → agent should fallback to LLM-only response
- If Supabase is unreachable → return error but don't expose stack traces
- No API keys should appear in logs or error responses
- Tool timeouts prevent hanging indefinitely

**Interview answer:**
> "We wrap all tool calls in try/except blocks. If the MCP server is down, the agent catches the connection error and returns a friendly message like 'Trends data is temporarily unavailable.' If Tavily fails, the agent falls back to its own knowledge. We never expose stack traces to the client — errors are logged server-side with request IDs. API keys are loaded from environment variables and never included in responses or logs."

---

## 📋 7. TEST CASES — What Each One Tests & What You Must Do

### Authentication Tests (AUTH-01 to AUTH-04)

| Test ID | What It Tests | What You Must Build |
|---------|---------------|---------------------|
| AUTH-01 | User signup with email/password | Backend: `/auth/signup` endpoint → creates user in Supabase. Frontend: signup form → calls endpoint → redirects to chat |
| AUTH-02 | Login with valid/invalid credentials | Backend: `/auth/login` endpoint → returns JWT on success, error on failure. Frontend: login form → handles both cases |
| AUTH-03 | Chat API without token returns 401/403 | Backend: middleware checks Bearer token on `/chat` endpoints. No token = denied |
| AUTH-04 | Random/invalid tokens blocked | Backend: middleware validates JWT signature. Garbage tokens = rejected |

---

### Streaming Tests (STREAM-01 to STREAM-03)

| Test ID | What It Tests | What You Must Build |
|---------|---------------|---------------------|
| STREAM-01 | Response tokens appear incrementally | Backend: SSE endpoint streams LangChain agent tokens. Frontend: EventSource reads and displays them one by one |
| STREAM-02 | Tool activity shown in UI | Backend: SSE sends special events like `{"type":"tool_start","name":"tavily"}`. Frontend: shows "Searching web…" indicator |
| STREAM-03 | Refresh doesn't duplicate messages | Frontend: loads history from Supabase, doesn't re-add streamed messages. Backend: idempotent message storage |

---

### Tool Tests (TOOL-01 to TOOL-04)

| Test ID | What It Tests | What You Must Build |
|---------|---------------|---------------------|
| TOOL-01 | Tavily search works | Backend: `tools/tavily.py` → LangChain tool wrapping Tavily API. Agent invokes it for web search prompts |
| TOOL-02 | Google Trends MCP works | Backend: `tools/google_trends_mcp.py` → LangChain MCP adapter connecting to MCP container. Agent invokes it for trends prompts |
| TOOL-03 | Agent picks correct tool | Backend: ReAct agent only calls tools when needed. "What is SSE?" should NOT trigger MCP or Tavily |
| TOOL-04 | MCP down = graceful fallback | Backend: try/except around MCP calls. When MCP container stopped, agent says "unavailable" instead of crashing |

---

### Database Tests (DB-01 to DB-04)

| Test ID | What It Tests | What You Must Build |
|---------|---------------|---------------------|
| DB-01 | Messages saved with all fields | Supabase table: `messages(id, user_id, conversation_id, role, content, timestamp)`. Backend saves every message |
| DB-02 | Chat history restored on reload | Backend: endpoint to fetch messages by conversation_id. Frontend: loads on page mount |
| DB-03 | User A can't see User B's chats | Supabase: RLS policy `auth.uid() = user_id`. Test: login as B, B sees empty chat |
| DB-04 | Agent remembers context | Backend: loads full conversation into agent context. "My name is Fazal" → later "What's my name?" → "Fazal" |

---

### API Security Tests (API-01 to API-03)

| Test ID | What It Tests | What You Must Build |
|---------|---------------|---------------------|
| API-01 | Missing fields → 422 | Backend: Pydantic schemas validate request bodies. Missing `message` field = 422 error |
| API-02 | No secrets in logs/responses | Backend: filter API keys from logs. Never return stack traces to client |
| API-03 | CORS enforcement | Backend: FastAPI CORS middleware allows only frontend origin. Random origins blocked |

---

### Docker Tests (DOCKER-01 to DOCKER-03)

| Test ID | What It Tests | What You Must Build |
|---------|---------------|---------------------|
| DOCKER-01 | `docker compose up --build` works | `docker-compose.yml` with frontend, backend, google-trends-mcp services |
| DOCKER-02 | Backend connects to MCP via Docker network | Backend uses `http://google-trends-mcp:8080/mcp` (NOT localhost) |
| DOCKER-03 | Health checks pass | Backend `/health` → OK. MCP `/healthz` → OK |

---

## 🏗️ 8. IMPLEMENTATION ORDER (Recommended)

### Phase 1: Infrastructure Setup
1. Create `docker-compose.yml` with all 3 services
2. Set up Supabase project + tables + RLS policies
3. Create root `.env.example`

### Phase 2: Backend Core
4. Create `backend/` folder structure
5. Build `app/main.py` with FastAPI + CORS
6. Build `app/middleware/` with Supabase JWT validation
7. Build `app/routers/auth.py` (signup + login via Supabase)
8. Build `app/routers/health.py`
9. Build `app/services/db/` (Supabase client for messages)

### Phase 3: Agent & Tools
10. Build `app/services/tools/tavily.py` (Tavily tool)
11. Build `app/services/tools/google_trends_mcp.py` (MCP adapter)
12. Build `app/services/agent/` (LangChain ReAct agent with both tools)
13. Build `app/routers/chat.py` (SSE streaming endpoint)

### Phase 4: Frontend
14. Create React + TypeScript project with Vite
15. Build Login/Signup pages
16. Build Chat page with SSE streaming
17. Add tool activity indicators
18. Add auth state management
19. Build Dockerfile

### Phase 5: Integration & Testing
20. Test `docker compose up --build`
21. Run through all AUTH tests
22. Run through all STREAM tests
23. Run through all TOOL tests
24. Run through all DB tests
25. Run through all API security tests
26. Run through all DOCKER tests

---

## 🔑 9. KEY ENVIRONMENT VARIABLES NEEDED

### Backend `.env`
```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_JWT_SECRET=your-jwt-secret

# LLM
OPENAI_API_KEY=your-openai-key

# Tavily
TAVILY_API_KEY=your-tavily-key

# MCP Server
MCP_SERVER_URL=http://google-trends-mcp:8080/mcp

# CORS
FRONTEND_URL=http://localhost:3000
```

### MCP Server `.env`
```env
MCP_JWT_AUDIENCE=your-audience
MCP_JWT_ISSUER=your-issuer
MCP_JWT_PUBLIC_KEY=your-public-key
# OR
MCP_JWT_JWKS_URL=your-jwks-url
MCP_JWT_ALGORITHMS=RS256
```

### Frontend `.env`
```env
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

---

## ⚠️ 10. KNOWN ISSUES IN EXISTING CODE

1. **`security/verification.py`** — `_get_jwt_signing_key()` is defined TWICE (lines 10-19 and 23-32). This is likely a copy-paste bug. The second definition overwrites the first. Should remove one.

2. **`security/utils.py`** — `get_request_auth()` extracts `XGAAccessToken` and `XGTeamID` headers which seem specific to ClickUp, not this project. May not be relevant.

3. **`load_var.py`** — Default audience is `"clickup-mcp"` which should probably be changed for your project.

4. **No `.env.example`** — The MCP server needs JWT environment variables but no example file exists.

---

## 📊 11. SUPABASE TABLE SCHEMA (What to Create)

### Option A: Single Messages Table (Minimum)
```sql
CREATE TABLE messages (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  conversation_id UUID NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Enable RLS
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Users can only access their own messages
CREATE POLICY "Users read own messages" ON messages
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users insert own messages" ON messages
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Index for fast lookups
CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at);
CREATE INDEX idx_messages_user ON messages(user_id);
```

### Option B: Conversations + Messages (Recommended by test doc)
```sql
CREATE TABLE conversations (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  title TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE messages (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE NOT NULL,
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  tool_calls JSONB,             -- Stores tool call metadata (recommended improvement)
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Enable RLS on both tables
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Conversation policies
CREATE POLICY "Users read own conversations" ON conversations
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users insert own conversations" ON conversations
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Message policies
CREATE POLICY "Users read own messages" ON messages
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users insert own messages" ON messages
  FOR INSERT WITH CHECK (auth.uid() = user_id);
```

---

## 📝 12. DOCKER COMPOSE TEMPLATE

```yaml
version: "3.8"

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    depends_on:
      - google-trends-mcp

  google-trends-mcp:
    build: .
    ports:
      - "8080:8080"
    env_file:
      - ./.env
```

---

## 🎯 13. SUMMARY CHECKLIST

### Must Build:
- [ ] Frontend (React + TypeScript + Dockerfile)
- [ ] Backend (FastAPI + LangChain + Dockerfile)
- [ ] LangChain ReAct Agent with tool selection
- [ ] Tavily Web Search Tool integration
- [ ] LangChain MCP Adapter for Google Trends
- [ ] Supabase Auth (signup/login)
- [ ] Supabase Chat Memory (save/load/isolate)
- [ ] SSE Streaming from backend to frontend
- [ ] Tool activity indicators in UI
- [ ] Auth Middleware on backend
- [ ] Docker Compose for full orchestration
- [ ] Supabase Tables + RLS Policies

### Must Understand:
- [ ] SSE vs WebSocket (and why SSE)
- [ ] How ReAct agent picks tools
- [ ] How MCP adapter connects to MCP server
- [ ] How Supabase RLS prevents data leaks
- [ ] How chat memory is loaded into agent
- [ ] How middleware blocks unauthorized access
- [ ] Docker networking (service names, not localhost)
- [ ] Failure handling strategy

### Already Done:
- [x] Google Trends MCP Server (all 5 tools)
- [x] MCP JWT Authentication
- [x] MCP Dockerfile
- [x] MCP Health Check (`/healthz`)
