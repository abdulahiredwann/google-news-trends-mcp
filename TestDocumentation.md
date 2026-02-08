
End-to-End Test Requirements
Frontend (React TS) + Backend (FastAPI) + Supabase + Google Trends MCP + Tavily + Docker Compose

1) System scope (updated)
Core system
A LangChain ReAct chatbot with:
Google Trends MCP (already hosted on its own Docker container/port)
Tavily Web Search (free API)
LangChain MCP Adapter
Streaming responses to frontend
Supabase for:
Email/password auth
Chat memory persistence
FastAPI backend with strict middleware access control
React + TypeScript frontend
Docker Compose orchestration

2) Required deliverables
Frontend
React + TypeScript
Login (email + password)
Streaming chat UI
Tool activity indicators (e.g. “Searching web…”, “Fetching trends…”)
Dockerfile


Backend
FastAPI
Auth + middleware
LangChain ReAct agent
Tools:
Google Trends MCP (external container)
Tavily search
Streaming API (SSE preferred)
Supabase integration
Dockerfile





Infrastructure
Supabase tables + RLS
Docker Compose where all containers communicate

3) Folder structure (mandatory consistency)
Frontend
frontend/
 ├─ src/
 │  ├─ api/
 │  ├─ components/
 │  ├─ pages/
 │  ├─ state/
 │  ├─ types/
 │  └─ utils/
 ├─ Dockerfile
 ├─ package.json
 └─ .env.example

Backend
backend/
 ├─ app/
 │  ├─ main.py
 │  ├─ core/
 │  ├─ middleware/
 │  ├─ routers/
 │  │  ├─ auth.py
 │  │  ├─ chat.py
 │  │  └─ health.py
 │  ├─ schemas/
 │  ├─ services/
 │  │  ├─ agent/
 │  │  ├─ tools/
 │  │  │  ├─ tavily.py
 │  │  │  └─ google_trends_mcp.py
 │  │  └─ db/
 │  └─ utils/
 ├─ Dockerfile
 ├─ requirements.txt
 └─ .env.example

Root
docker-compose.yml
README.md
.env.example


4) Authentication & middleware tests
AUTH-01: Signup
User creates account with email/password
Stored in Supabase
Redirect to chat
AUTH-02: Login
Valid credentials → success
Invalid credentials → error
AUTH-03: Middleware protection
Chat API called without token
❌ Access denied (401/403)
AUTH-04: Unknown access blocked
Random headers / invalid tokens
Middleware rejects request cleanly

5) Streaming chat tests
STREAM-01: Token streaming
Prompt: “Hello”
Assistant response appears incrementally
STREAM-02: Tool activity events
Prompt: “Search the web for LangChain agents”
UI shows:
“Searching web…”
“Summarizing…”
STREAM-03: Reconnect safety
Refresh during streaming
No duplicated messages
Conversation remains intact

6) Tooling tests (ReAct agent)
TOOL-01: Tavily search
Prompt: “Find what Tavily API does”
Expected:
Tavily tool invoked
Clean summarized output
TOOL-02: Google Trends MCP
Prompt: “Check Google Trends for ‘AI agents’”
Expected:
MCP server called
Trends data returned gracefully
TOOL-03: Correct tool selection
Prompt: “What is SSE streaming?”
Expected:
❌ No trends MCP call
Optional Tavily or pure LLM reasoning
TOOL-04: MCP down handling
Stop MCP container
Ask trends question
Expected:
Friendly error or fallback
Backend does NOT crash

7) Supabase chat memory tests
DB-01: Save messages
Messages saved with:
user_id
conversation_id
role
content
timestamp
DB-02: Restore memory
Reload page
Chat history restored
DB-03: User isolation
User A chats
User B logs in
❌ User B cannot see User A chats
DB-04: Memory usage
User: “My name is Fazal”
Later: “What’s my name?”
Agent remembers correctly

8) API security & validation
API-01: Request validation
Missing fields → 422
API-02: Secrets safety
No API keys in logs
No stack traces in client responses
API-03: CORS enforcement
Frontend allowed
Random origins blocked (if configured)

9) Docker & networking tests
DOCKER-01: One-command startup
docker compose up --build

All services start cleanly
DOCKER-02: MCP connectivity
Backend connects to Google Trends MCP via docker network
❌ No localhost hardcoding
DOCKER-03: Health checks
Backend /health → OK
MCP ready signal/logs present

10) Review / interview questions (they will be asked)
Builder must explain:
Why SSE vs WebSocket
How ReAct agent decides between:
Tavily
Google Trends MCP
How MCP adapter is wired
How Supabase RLS prevents data leaks
How chat memory is loaded into the agent
How middleware blocks unknown access
Docker networking decisions
Failure handling strategy

11) Recommended improvements (strongly appreciated)
Conversation/message table separation
Tool call metadata storage
Request-scoped logging (user_id + request_id)
Agent iteration limits
Tool timeouts
Graceful fallback responses
Minimal exposed ports
.env.example for all services

12) Final acceptance criteria
✅ Login works
✅ Streaming chat works
✅ Google Trends MCP works
✅ Tavily search works
✅ Chat saved in Supabase
✅ User isolation enforced
✅ Middleware blocks unknown access
✅ Clean folder structure
✅ All services connected via Docker Compose


