# 📋 Task Tracker — Google News Trends Full Stack Project

> Last updated: Feb 8, 2026
> Reference: TestDocumentation.md

---

## ✅ PHASE 0 — MCP Server (Pre-existing)

| # | Task | Status |
|---|------|--------|
| 0.1 | Google Trends MCP server (`main.py`, `mcp_server.py`, `tools.py`) | ✅ Done |
| 0.2 | MCP JWT auth middleware (`security/verification.py`) | ✅ Done |
| 0.3 | MCP Dockerfile (upgraded to Python 3.12 + Playwright) | ✅ Done |
| 0.4 | MCP health check `/healthz` | ✅ Done |
| 0.5 | 5 MCP tools (news by keyword/location/topic, top news, trending terms) | ✅ Done |
| 0.6 | MCP Docker container built & running on port 8080 | ✅ Done |

---

## ✅ PHASE 1 — Frontend Setup

| # | Task | Status |
|---|------|--------|
| 1.1 | Create React + TypeScript project (Vite) in `frontend/` | ✅ Done |
| 1.2 | Install & configure Tailwind CSS v4 | ✅ Done |
| 1.3 | Install & configure shadcn/ui components | ✅ Done |
| 1.4 | Path alias `@/` setup in tsconfig + vite | ✅ Done |
| 1.5 | Create `LoginPage.tsx` (email + password, login/signup toggle) | ✅ Done |
| 1.6 | Create `ChatPage.tsx` (messages, input, tool activity indicator) | ✅ Done |
| 1.7 | Setup react-router-dom routing (`/` → Login, `/chat` → Chat) | ✅ Done |
| 1.8 | Create folder structure (`api/`, `state/`, `types/`, `utils/`) | ✅ Done |
| 1.9 | shadcn components: button, input, label, card, avatar, scroll-area | ✅ Done |

---

## ✅ PHASE 2 — Backend Core

| # | Task | Status | Details |
|---|------|--------|---------|
| 2.1 | Create `backend/` folder structure | ✅ Done | `app/main.py`, `core/`, `middleware/`, `routers/`, `schemas/`, `services/`, `utils/` |
| 2.2 | `requirements.txt` with all dependencies | ✅ Done | fastapi, uvicorn, langchain, supabase, tavily, etc. |
| 2.3 | `app/core/config.py` — settings & env vars | ✅ Done | All env vars loaded |
| 2.4 | `app/main.py` — FastAPI app + CORS | ✅ Done | Mount routers, CORS middleware |
| 2.5 | `app/routers/health.py` — `/health` endpoint | ✅ Done | Returns `{"status": "ok"}` |
| 2.6 | `app/middleware/auth.py` — JWT validation middleware | ✅ Done | Validates Supabase JWT, sets `request.state.user_id` + `access_token` |
| 2.7 | `app/routers/auth.py` — signup + login endpoints | ✅ Done | POST `/auth/signup`, POST `/auth/login` |
| 2.8 | `app/schemas/` — Pydantic models | ✅ Done | AuthRequest, ChatRequest, MessageOut, ConversationOut |
| 2.9 | `app/services/db/supabase.py` — Supabase client + CRUD | ✅ Done | save_message(), get_messages(), get_conversations() with user JWT |
| 2.10 | `backend/.env` + `.env.example` | ✅ Done | Supabase + MCP creds configured |
| 2.11 | `backend/Dockerfile` | ⬜ Pending | Deferred to Phase 6 |

---

## ✅ PHASE 3 — LangChain Agent & Tools

| # | Task | Status | Details |
|---|------|--------|---------|
| 3.1 | `app/services/tools/tavily.py` — Tavily search tool | ✅ Done | Wraps Tavily API as LangChain tool |
| 3.2 | `app/services/tools/google_trends_mcp.py` — MCP adapter | ✅ Done | Passes user JWT, uses `langchain-mcp-adapters` v0.1.0 API |
| 3.3 | `app/services/agent/react_agent.py` — ReAct agent | ✅ Done | `create_react_agent` with tools + chat memory + streaming |
| 3.4 | `app/routers/chat.py` — SSE streaming endpoint | ✅ Done | POST `/chat/send` → SSE events (token, tool_start, tool_end, done) |
| 3.5 | Chat memory loading from Supabase | ✅ Done | Loads conversation history before each agent call |

---

## ✅ PHASE 4 — Frontend ↔ Backend Integration

| # | Task | Status | Details |
|---|------|--------|---------|
| 4.1 | `src/api/client.ts` — base fetch wrapper with auth headers | ✅ Done | Auto-attaches JWT, handles 401 redirect |
| 4.2 | `src/api/auth.ts` — login/signup API client | ✅ Done | Calls backend `/auth/login`, `/auth/signup` |
| 4.3 | `src/api/chat.ts` — SSE streaming client | ✅ Done | `streamChat()` parses SSE events in real-time |
| 4.4 | `src/state/auth.tsx` — AuthProvider context | ✅ Done | Token + user in React context + localStorage |
| 4.5 | `src/types/auth.ts` + `src/types/chat.ts` — TypeScript types | ✅ Done | AuthRequest, AuthResponse, User, Message, SSEEvent |
| 4.6 | `src/components/ProtectedRoute.tsx` — route guard | ✅ Done | Redirects to `/` if not authenticated |
| 4.7 | Wire LoginPage to real auth endpoints | ✅ Done | Calls login/signup, stores token, shows loading/error |
| 4.8 | Wire ChatPage to real SSE streaming | ✅ Done | Streams tokens, shows tool activity, tracks conversation |
| 4.9 | App.tsx wrapped with AuthProvider + ProtectedRoute | ✅ Done | `/chat` is protected |

---

## ✅ PHASE 5 — Supabase Setup

| # | Task | Status | Details |
|---|------|--------|---------|
| 5.1 | Create Supabase project | ✅ Done | URL + anon key configured |
| 5.2 | Create `messages` table | ✅ Done | id, conversation_id, user_id, role, content, created_at |
| 5.3 | Enable RLS + policies | ✅ Done | read_own_messages + insert_own_messages policies |
| 5.4 | Create indexes for performance | ✅ Done | idx_messages_user_conv_time |
| 5.5 | Disable email confirmation (dev) | ✅ Done | For faster dev testing |

---

## ✅ PHASE 4b — UI Enhancements (Extra)

| # | Task | Status | Details |
|---|------|--------|---------|
| 4b.1 | Chat history persistence (conversationId in localStorage) | ✅ Done | Reload page restores conversation |
| 4b.2 | Load messages from backend on mount | ✅ Done | `getMessages()` + `getConversations()` |
| 4b.3 | Sidebar with conversation list | ✅ Done | Shows title + time, switch conversations, new chat |
| 4b.4 | Dark / Light mode + ThemeToggle | ✅ Done | ThemeProvider, persists in localStorage, system pref detection |
| 4b.5 | Skeleton loaders (sidebar + chat) | ✅ Done | Replaced spinners/text with skeleton placeholders |

---

## ⬜ PHASE 6 — Docker Compose

| # | Task | Status | Details |
|---|------|--------|---------|
| 6.1 | `frontend/Dockerfile` | ⬜ Pending | Build React app, serve with nginx |
| 6.2 | `backend/Dockerfile` | ⬜ Pending | Python, pip install, uvicorn |
| 6.3 | `docker-compose.yml` | ⬜ Pending | frontend + backend + google-trends-mcp services |
| 6.4 | Docker networking (service names, no localhost) | ⬜ Pending | Backend → `http://google-trends-mcp:8080/mcp/` |
| 6.5 | Root `.env.example` | ⬜ Pending | All env vars for all services |
| 6.6 | Test `docker compose up --build` | ⬜ Pending | All services start cleanly |

---

## ⬜ PHASE 7 — Testing & Polish

| # | Task | Status | Details |
|---|------|--------|---------|
| 7.1 | AUTH-01: Signup works | ⬜ Pending | |
| 7.2 | AUTH-02: Login works (valid + invalid) | ⬜ Pending | |
| 7.3 | AUTH-03: Chat API without token → 401 | ⬜ Pending | |
| 7.4 | AUTH-04: Invalid tokens rejected | ⬜ Pending | |
| 7.5 | STREAM-01: Tokens stream incrementally | ⬜ Pending | |
| 7.6 | STREAM-02: Tool activity events shown | ⬜ Pending | |
| 7.7 | STREAM-03: Refresh doesn't duplicate | ⬜ Pending | |
| 7.8 | TOOL-01: Tavily search works | ⬜ Pending | |
| 7.9 | TOOL-02: Google Trends MCP works | ⬜ Pending | |
| 7.10 | TOOL-03: Correct tool selection | ⬜ Pending | |
| 7.11 | TOOL-04: MCP down → graceful fallback | ⬜ Pending | |
| 7.12 | DB-01: Messages saved correctly | ⬜ Pending | |
| 7.13 | DB-02: Chat history restored on reload | ⬜ Pending | |
| 7.14 | DB-03: User isolation (RLS) | ⬜ Pending | |
| 7.15 | DB-04: Agent remembers context | ⬜ Pending | |
| 7.16 | API-01: Missing fields → 422 | ⬜ Pending | |
| 7.17 | API-02: No secrets in logs/responses | ⬜ Pending | |
| 7.18 | API-03: CORS enforcement | ⬜ Pending | |
| 7.19 | DOCKER-01: One-command startup | ⬜ Pending | |
| 7.20 | DOCKER-02: MCP connectivity via Docker network | ⬜ Pending | |
| 7.21 | DOCKER-03: Health checks pass | ⬜ Pending | |

---

## 📊 Progress Summary

| Phase | Description | Tasks | Done | Remaining |
|-------|-------------|-------|------|-----------|
| 0 | MCP Server (pre-existing) | 6 | 6 | 0 |
| 1 | Frontend Setup | 9 | 9 | 0 |
| 2 | Backend Core | 11 | 10 | 1 |
| 3 | Agent & Tools | 5 | 5 | 0 |
| 4 | Frontend ↔ Backend Integration | 9 | 9 | 0 |
| 4b | UI Enhancements | 5 | 5 | 0 |
| 5 | Supabase Setup | 5 | 5 | 0 |
| 6 | Docker Compose | 6 | 0 | 6 |
| 7 | Testing & Polish | 21 | 0 | 21 |
| **Total** | | **77** | **49** | **28** |

---

## 🔜 NEXT STEP → Phase 6: Docker Compose

### Tasks:
1. Create `frontend/Dockerfile` — multi-stage build (npm build → nginx)
2. Create `backend/Dockerfile` — Python 3.12, pip install, uvicorn
3. Create `docker-compose.yml` — orchestrate all 3 services
4. Docker networking — services talk via container names (no localhost)
5. Root `.env.example` — all env vars documented
6. Test `docker compose up --build`

> 💡 Tell Cursor: "Let's do Phase 6 — Docker Compose"
