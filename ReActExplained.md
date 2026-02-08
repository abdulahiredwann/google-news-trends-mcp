# 🧠 ReAct Agent & LangChain — How the Backend Works (Detailed)

> This document explains every piece of the AI agent backend, how ReAct works, what LangChain does, and how all the files connect together.

---

## 📖 Table of Contents

1. [What is ReAct?](#1-what-is-react)
2. [What is LangChain / LangGraph?](#2-what-is-langchain--langgraph)
3. [The Full Request Flow (Step by Step)](#3-the-full-request-flow)
4. [File-by-File Breakdown](#4-file-by-file-breakdown)
5. [How SSE Streaming Works](#5-how-sse-streaming-works)
6. [How Chat Memory Works](#6-how-chat-memory-works)
7. [How Tools Work](#7-how-tools-work)
8. [How MCP Integration Works](#8-how-mcp-integration-works)
9. [Diagram: Complete Architecture](#9-diagram-complete-architecture)
10. [Key Libraries Used](#10-key-libraries-used)

---

## 1. What is ReAct?

**ReAct** stands for **Re**asoning + **Act**ing. It's a pattern where an AI agent:

1. **Thinks** — Reasons about what to do next
2. **Acts** — Calls a tool (search the web, check trends, etc.)
3. **Observes** — Reads the tool's result
4. **Repeats** — Decides if it needs more info or can answer

### Example: User asks "What's trending on Google today?"

```
Step 1 — THINK:  "The user wants Google Trends data. I should use the 
                  google_trends_trending_terms tool."

Step 2 — ACT:    Call tool: google_trends_trending_terms(geo="US")

Step 3 — OBSERVE: Tool returns: ["AI regulation", "Super Bowl", "Bitcoin", ...]

Step 4 — THINK:  "I have the trending data. I can now give a nice summary."

Step 5 — RESPOND: "Here are today's trending topics on Google: 
                   1. AI regulation  2. Super Bowl  3. Bitcoin ..."
```

### Without ReAct (normal chatbot):
```
User: "What's trending on Google?"
AI:   "I don't have access to real-time data." ← STUCK, can't do anything
```

### With ReAct (our agent):
```
User: "What's trending on Google?"
AI:   *thinks* → *calls Google Trends tool* → *reads result* → gives real answer
```

**The key idea: the LLM decides WHICH tool to use, WHEN to use it, and HOW to combine results.**

---

## 2. What is LangChain / LangGraph?

### LangChain
LangChain is a Python framework that makes it easy to build AI applications. It provides:

- **LLM wrappers** — Talk to OpenAI, Anthropic, etc. with a unified API
- **Tools** — Wrap any function/API as a "tool" the AI can call
- **Messages** — `HumanMessage`, `AIMessage`, `SystemMessage` for chat history
- **Streaming** — Get the AI's response token-by-token (not all at once)

### LangGraph
LangGraph is built on top of LangChain. It provides:

- **`create_react_agent`** — A pre-built ReAct agent that handles the Think→Act→Observe loop
- **`astream_events`** — Stream every event (tokens, tool calls, tool results) as they happen

### In our code:

| Library | Import | What it does |
|---------|--------|-------------|
| `langchain_openai` | `ChatOpenAI` | Talks to OpenAI's GPT-4o-mini |
| `langgraph.prebuilt` | `create_react_agent` | Creates the ReAct agent loop |
| `langchain_core.messages` | `HumanMessage, AIMessage, SystemMessage` | Chat history format |
| `langchain_community.tools` | `TavilySearchResults` | Web search tool |
| `langchain_mcp_adapters` | `MultiServerMCPClient` | Connects to MCP server tools |

---

## 3. The Full Request Flow

Here's exactly what happens when a user sends a message:

```
┌──────────────┐     POST /chat/send      ┌──────────────────┐
│   Frontend   │ ──────────────────────── │   FastAPI Backend │
│  (React App) │    { message, token }     │    (chat.py)      │
└──────────────┘                           └────────┬─────────┘
                                                    │
                                        ┌───────────▼──────────────┐
                                        │  Step 1: Auth Middleware  │
                                        │  Verify JWT with Supabase│
                                        │  Extract user_id         │
                                        └───────────┬──────────────┘
                                                    │
                                        ┌───────────▼──────────────┐
                                        │  Step 2: Save user msg   │
                                        │  to Supabase messages    │
                                        └───────────┬──────────────┘
                                                    │
                                        ┌───────────▼──────────────┐
                                        │  Step 3: Load MCP tools  │
                                        │  Connect to MCP Docker   │
                                        │  container, get 5 tools  │
                                        └───────────┬──────────────┘
                                                    │
                                        ┌───────────▼──────────────┐
                                        │  Step 4: Load chat       │
                                        │  history from Supabase   │
                                        │  (for memory/context)    │
                                        └───────────┬──────────────┘
                                                    │
                                        ┌───────────▼──────────────┐
                                        │  Step 5: Create ReAct    │
                                        │  agent with LangGraph    │
                                        │  (LLM + Tools + Prompt)  │
                                        └───────────┬──────────────┘
                                                    │
                                        ┌───────────▼──────────────┐
                                        │  Step 6: Agent runs      │
                                        │  Think → Act → Observe   │
                                        │  loop (may call tools)   │
                                        └───────────┬──────────────┘
                                                    │
                                        ┌───────────▼──────────────┐
                                        │  Step 7: Stream events   │
                                        │  via SSE back to frontend│
                                        │  (token, tool_start, etc)│
                                        └───────────┬──────────────┘
                                                    │
                                        ┌───────────▼──────────────┐
                                        │  Step 8: Save assistant  │
                                        │  response to Supabase    │
                                        └──────────────────────────┘
```

---

## 4. File-by-File Breakdown

### `backend/app/main.py` — The Entry Point

```python
app = FastAPI(title=settings.APP_NAME)

# 1. CORS middleware — allows frontend (localhost:5173) to call backend
app.add_middleware(CORSMiddleware, ...)

# 2. Auth middleware — checks JWT on every request (except /health, /auth/*)
app.add_middleware(AuthMiddleware)

# 3. Mount route handlers
app.include_router(health.router)   # GET /health
app.include_router(auth.router)     # POST /auth/login, /auth/signup
app.include_router(chat.router)     # POST /chat/send, GET /chat/conversations
```

**What it does:** Sets up the FastAPI application. Every request goes through CORS → Auth → Router.

---

### `backend/app/middleware/auth.py` — JWT Protection

```python
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 1. Skip public paths (/health, /auth/login, /auth/signup)
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # 2. Extract "Bearer <token>" from Authorization header
        token = auth_header.split(" ", 1)[1]

        # 3. Verify token by calling Supabase: GET /auth/v1/user
        response = await client.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={"Authorization": f"Bearer {token}", "apikey": SUPABASE_KEY}
        )

        # 4. If valid → attach user_id and token to the request
        request.state.user_id = user_data["id"]
        request.state.access_token = token

        # 5. If invalid → return 401
```

**What it does:** Every protected request must have a valid Supabase JWT. The middleware verifies it and passes `user_id` to the route handler.

---

### `backend/app/core/config.py` — Environment Variables

```python
class Settings(BaseSettings):
    SUPABASE_URL: str = ""          # Supabase project URL
    SUPABASE_KEY: str = ""          # Supabase anon key
    OPENAI_API_KEY: str = ""        # For GPT-4o-mini
    TAVILY_API_KEY: str = ""        # For web search (optional)
    MCP_SERVER_URL: str = "..."     # Google Trends MCP server
    FRONTEND_URL: str = "..."       # For CORS

    model_config = { "env_file": ".env" }  # ← reads from backend/.env
```

**What it does:** Loads all secrets from `.env` file once at startup. All other files use `settings.OPENAI_API_KEY`, etc.

---

### `backend/app/routers/chat.py` — The Chat Endpoint (Orchestrator)

This is the **most important file** — it ties everything together:

```python
@router.post("/send")
async def send_message(req: ChatRequest, request: Request):
    user_id = request.state.user_id     # From auth middleware
    token = request.state.access_token   # From auth middleware

    # 1. Save user message to Supabase
    save_message(conversation_id, user_id, "user", req.message, token)

    async def event_generator():
        # 2. Try to load MCP tools (Google Trends)
        try:
            config = get_mcp_client_config(access_token=token)
            mcp_client = MultiServerMCPClient(config)
            mcp_tools = await mcp_client.get_tools()  # ← 5 Google Trends tools
        except:
            mcp_tools = []  # MCP down? Continue without it

        # 3. Run the ReAct agent with streaming
        async for event in run_agent_stream(
            user_message=req.message,
            conversation_id=conversation_id,
            user_id=user_id,
            access_token=token,
            mcp_tools=mcp_tools,       # ← pass MCP tools to agent
        ):
            # 4. Forward events to frontend via SSE
            if event["type"] == "token":
                yield {"event": "token", "data": {"content": "Hello"}}
            elif event["type"] == "tool_start":
                yield {"event": "tool_start", "data": {"tool": "tavily_search"}}
            elif event["type"] == "tool_end":
                yield {"event": "tool_end", "data": {"tool": "tavily_search"}}

        # 5. Save assistant response to Supabase
        save_message(conversation_id, user_id, "assistant", full_response, token)

        # 6. Signal completion
        yield {"event": "done", "data": {"conversation_id": "..."}}

    return EventSourceResponse(event_generator())
```

**What it does:**
- Receives user message
- Saves it to Supabase
- Loads MCP tools (if available)
- Runs the ReAct agent
- Streams every token/tool event back to frontend as SSE
- Saves the final response to Supabase

---

### `backend/app/services/agent/react_agent.py` — The Brain 🧠

This is where LangChain's ReAct agent lives:

#### Part 1: System Prompt
```python
SYSTEM_PROMPT = """You are a helpful AI assistant with access to tools.
You can search the web using Tavily and check Google Trends/News using the MCP tools.

Guidelines:
- Use tavily_search when the user wants to find information on the web
- Use Google Trends MCP tools when the user asks about trending topics
- If general knowledge question, answer without tools
- Summarize tool results naturally
"""
```
This tells the LLM **who it is** and **when to use which tool**.

#### Part 2: Build Chat History (Memory)
```python
def build_chat_history(messages: list[dict]) -> list:
    """Convert Supabase messages → LangChain message objects"""
    for msg in messages:
        if msg["role"] == "user":
            history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            history.append(AIMessage(content=msg["content"]))
```
This loads the previous conversation so the agent **remembers what was said before**.

#### Part 3: Create the LLM
```python
def get_llm():
    return ChatOpenAI(
        model="gpt-4o-mini",    # The AI model
        temperature=0,           # Deterministic (no randomness)
        streaming=True,          # Token-by-token output
    )
```

#### Part 4: Create the ReAct Agent
```python
async def create_agent(mcp_tools=None):
    tools = []

    # Add Tavily web search (if API key is set)
    tavily = get_tavily_tool()
    if tavily:
        tools.append(tavily)

    # Add Google Trends MCP tools (if MCP server is up)
    if mcp_tools:
        tools.extend(mcp_tools)  # ← up to 5 tools from MCP

    llm = get_llm()

    # THIS IS THE KEY LINE — creates the ReAct agent
    agent = create_react_agent(
        model=llm,          # GPT-4o-mini
        tools=tools,        # [tavily_search, mcp_tool_1, mcp_tool_2, ...]
        prompt=SYSTEM_PROMPT,
    )
    return agent
```

**`create_react_agent`** does all the magic:
- It wraps the LLM in a Think→Act→Observe loop
- It tells the LLM about all available tools (names + descriptions)
- When the LLM decides to call a tool, it executes it and feeds the result back
- It keeps looping until the LLM says "I have my final answer"

#### Part 5: Run with Streaming
```python
async def run_agent_stream(user_message, conversation_id, user_id, ...):
    # 1. Load chat history from Supabase (memory)
    stored_messages = get_messages(conversation_id, user_id)
    chat_history = build_chat_history(stored_messages)
    chat_history.append(HumanMessage(content=user_message))

    # 2. Create the agent
    agent = await create_agent(mcp_tools=mcp_tools)

    # 3. Stream every event
    async for event in agent.astream_events(
        {"messages": chat_history},  # ← full conversation so far
        version="v2",
    ):
        kind = event["event"]

        if kind == "on_tool_start":        # Agent decided to call a tool
            yield {"type": "tool_start", "tool": "tavily_search"}

        elif kind == "on_tool_end":        # Tool returned its result
            yield {"type": "tool_end", "tool": "tavily_search"}

        elif kind == "on_chat_model_stream":  # LLM is generating a word
            yield {"type": "token", "content": "Hello"}

    yield {"type": "done", "content": full_response}
```

**`astream_events`** is the streaming API from LangGraph. It fires events like:
- `on_tool_start` — "I'm about to call tavily_search"
- `on_tool_end` — "tavily_search returned results"
- `on_chat_model_stream` — "Here's the next word of my response"

---

### `backend/app/services/tools/tavily.py` — Web Search Tool

```python
def get_tavily_tool():
    tool = TavilySearchResults(
        max_results=5,
        name="tavily_search",
        description="Search the web for current information..."
    )
    return tool
```

**What it does:** Wraps the Tavily API as a LangChain "tool". The agent sees:
- **Name:** `tavily_search`
- **Description:** "Search the web for current information..."
- **Input:** A search query string

When the agent calls this tool, LangChain automatically:
1. Sends the query to Tavily's API
2. Returns the top 5 search results
3. Feeds them back to the agent so it can summarize

---

### `backend/app/services/tools/google_trends_mcp.py` — MCP Tool Adapter

```python
def get_mcp_client_config(access_token=""):
    config = {
        "google-trends": {
            "url": "http://localhost:8080/mcp/",    # MCP Docker container
            "transport": "streamable_http",          # Protocol
            "headers": {
                "Authorization": f"Bearer {access_token}",  # User's JWT
            },
        }
    }
    return config
```

**What it does:** Configures the connection to the Google Trends MCP server (running in Docker). The MCP server exposes 5 tools:
1. `get_news_by_keyword` — Search Google News by keyword
2. `get_news_by_location` — Get news for a specific country/city
3. `get_news_by_topic` — Get news by topic (tech, sports, etc.)
4. `get_top_news` — Get today's top headlines
5. `get_trending_terms` — Get trending search terms

The `langchain-mcp-adapters` library converts these MCP tools into LangChain tools automatically.

---

### `backend/app/services/db/supabase.py` — Database (Memory Storage)

```python
def save_message(conversation_id, user_id, role, content, access_token):
    """Saves a message to Supabase (user or assistant)"""
    client.table("messages").insert({
        "conversation_id": conversation_id,
        "user_id": user_id,
        "role": role,          # "user" or "assistant"
        "content": content,    # The actual text
    }).execute()

def get_messages(conversation_id, user_id, access_token):
    """Loads all messages for a conversation (for agent memory)"""
    client.table("messages")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
```

**What it does:** Every message (user + assistant) is saved to Supabase. Before each agent call, the full conversation history is loaded and passed to the agent so it **remembers previous messages**.

---

## 5. How SSE Streaming Works

**SSE = Server-Sent Events** — A way to stream data from server to browser in real-time.

```
Frontend                          Backend
   │                                │
   │  POST /chat/send               │
   │ ─────────────────────────────► │
   │                                │ Agent starts thinking...
   │  event: token                  │
   │  data: {"content": "Hello"}    │
   │ ◄───────────────────────────── │
   │                                │
   │  event: token                  │
   │  data: {"content": " world"}   │
   │ ◄───────────────────────────── │
   │                                │ Agent decides to use a tool...
   │  event: tool_start             │
   │  data: {"tool": "tavily"}      │
   │ ◄───────────────────────────── │
   │                                │ Tool returns results...
   │  event: tool_end               │
   │  data: {"tool": "tavily"}      │
   │ ◄───────────────────────────── │
   │                                │ Agent summarizes...
   │  event: token                  │
   │  data: {"content": "Based"}    │
   │ ◄───────────────────────────── │
   │  ...more tokens...             │
   │                                │
   │  event: done                   │
   │  data: {"conversation_id":...} │
   │ ◄───────────────────────────── │
   │                                │
```

The frontend parses each SSE event and:
- **`token`** → Appends text to the chat bubble (live typing effect)
- **`tool_start`** → Shows "Using tavily_search..." indicator
- **`tool_end`** → Hides the indicator
- **`done`** → Marks the response as complete

---

## 6. How Chat Memory Works

```
Conversation: abc-123

  Supabase messages table:
  ┌──────────────┬────────┬──────────────────────────────────┐
  │ conversation  │ role   │ content                          │
  ├──────────────┼────────┼──────────────────────────────────┤
  │ abc-123      │ user   │ "Hello! Who are you?"            │
  │ abc-123      │ assist │ "I'm an AI assistant..."         │
  │ abc-123      │ user   │ "What was my first message?"     │  ← NEW
  └──────────────┴────────┴──────────────────────────────────┘

When processing "What was my first message?":
  1. Load messages for abc-123 from Supabase
  2. Convert to LangChain format:
     [
       HumanMessage("Hello! Who are you?"),
       AIMessage("I'm an AI assistant..."),
       HumanMessage("What was my first message?")   ← append new
     ]
  3. Pass entire list to agent → agent sees full context
  4. Agent responds: "Your first message was 'Hello! Who are you?'"
```

**This is why the agent remembered your first message in our test!**

---

## 7. How Tools Work

The LLM doesn't call tools directly. Instead:

1. **LLM receives tool descriptions** (name + what it does)
2. **LLM outputs a special "tool call" message** (e.g., `call tavily_search("Bitcoin price")`)
3. **LangGraph intercepts this** and actually calls the tool
4. **Tool result is fed back** to the LLM as a "tool message"
5. **LLM reads the result** and either calls another tool or writes its final answer

```python
# What the LLM "sees" as available tools:
tools = [
    {
        "name": "tavily_search",
        "description": "Search the web for current information...",
        "input": "search query string"
    },
    {
        "name": "get_trending_terms",
        "description": "Get trending Google search terms...",
        "input": "geo location code"
    },
    # ... more MCP tools
]
```

The LLM's internal reasoning (simplified):
```
User: "What's trending on Google in the US?"

Thought: The user wants Google Trends data for the US. 
         I should use the get_trending_terms tool.
Action:  get_trending_terms(geo="US")
Result:  ["AI stocks", "Super Bowl", "Weather alert", ...]
Thought: I have the data. Let me present it nicely.
Answer:  "Here are the current trending searches in the US: ..."
```

---

## 8. How MCP Integration Works

**MCP = Model Context Protocol** — A standard way for AI tools to be served as a web service.

```
┌─────────────────┐                    ┌─────────────────────────┐
│   Our Backend   │   HTTP + JSON-RPC   │   MCP Docker Container  │
│   (FastAPI)     │ ──────────────────► │   (google-trends-mcp)   │
│                 │                     │                         │
│  Uses library:  │   1. "list tools"   │   Exposes 5 tools:      │
│  langchain-mcp- │ ──────────────────► │   - get_news_by_keyword │
│  adapters       │   Returns 5 tools   │   - get_news_by_location│
│                 │ ◄────────────────── │   - get_news_by_topic   │
│                 │                     │   - get_top_news        │
│                 │   2. "call tool X"  │   - get_trending_terms  │
│                 │ ──────────────────► │                         │
│                 │   Returns result    │   Uses Playwright to    │
│                 │ ◄────────────────── │   scrape Google News    │
└─────────────────┘                    └─────────────────────────┘
```

1. Backend connects to MCP at `http://localhost:8080/mcp/`
2. Sends user's **Supabase JWT** for authentication
3. MCP server verifies the JWT
4. Backend asks "what tools do you have?" → gets 5 tools
5. These tools are converted to LangChain format automatically
6. Agent can now call them just like any other tool

---

## 9. Diagram: Complete Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER'S BROWSER                               │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  React Frontend (localhost:5173)                              │   │
│  │                                                               │   │
│  │  LoginPage ──► AuthProvider ──► ChatPage                      │   │
│  │       │              │               │                        │   │
│  │  POST /auth/login    │         POST /chat/send (SSE)          │   │
│  │       │         localStorage        │                         │   │
│  │       │         (JWT token)         │                         │   │
│  └───────┼─────────────────────────────┼─────────────────────────┘   │
│          │                             │                             │
└──────────┼─────────────────────────────┼─────────────────────────────┘
           │                             │
           ▼                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (localhost:8000)                   │
│                                                                      │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────────────────┐  │
│  │ CORS        │──►│ Auth         │──►│ Route Handlers           │  │
│  │ Middleware   │   │ Middleware   │   │                          │  │
│  │             │   │ (verify JWT) │   │  /auth/login             │  │
│  │ Allow       │   │              │   │  /auth/signup            │  │
│  │ frontend    │   │ Sets:        │   │  /chat/send ─────────┐   │  │
│  │ origin      │   │ user_id      │   │  /chat/conversations │   │  │
│  │             │   │ access_token │   │  /health             │   │  │
│  └─────────────┘   └──────────────┘   └──────────────────┼───┘  │  │
│                                                          │      │  │
│                              ┌────────────────────────────▼──┐   │  │
│                              │     ReAct Agent               │   │  │
│                              │     (create_react_agent)      │   │  │
│                              │                               │   │  │
│                              │  LLM: GPT-4o-mini (OpenAI)   │   │  │
│                              │  Prompt: System instructions  │   │  │
│                              │  Memory: Chat history from DB │   │  │
│                              │                               │   │  │
│                              │  Tools:                       │   │  │
│                              │  ├── tavily_search            │   │  │
│                              │  ├── get_news_by_keyword      │   │  │
│                              │  ├── get_news_by_location     │   │  │
│                              │  ├── get_news_by_topic        │   │  │
│                              │  ├── get_top_news             │   │  │
│                              │  └── get_trending_terms       │   │  │
│                              └───────┬───────────┬───────────┘   │  │
│                                      │           │               │  │
│                                      ▼           ▼               │  │
│                              ┌────────────┐ ┌────────────────┐   │  │
│                              │ Tavily API │ │ MCP Server     │   │  │
│                              │ (web       │ │ (Docker:8080)  │   │  │
│                              │  search)   │ │ Google Trends  │   │  │
│                              └────────────┘ └────────────────┘   │  │
│                                                                   │  │
└───────────────────────────────────────────────────────────────────┘  │
                    │                                                   │
                    ▼                                                   │
          ┌──────────────────┐                                         │
          │     Supabase     │                                         │
          │                  │                                         │
          │  Auth (JWT)      │◄────────────────────────────────────────┘
          │  Database (RLS)  │
          │  - messages table│
          └──────────────────┘
```

---

## 10. Key Libraries Used

| Library | Version | Purpose | Where Used |
|---------|---------|---------|------------|
| `langchain-openai` | latest | Talk to GPT-4o-mini | `react_agent.py` → `ChatOpenAI` |
| `langgraph` | latest | ReAct agent framework | `react_agent.py` → `create_react_agent` |
| `langchain-core` | latest | Message types, base classes | `react_agent.py` → `HumanMessage`, etc. |
| `langchain-community` | latest | Community tools (Tavily) | `tavily.py` → `TavilySearchResults` |
| `langchain-mcp-adapters` | 0.1.0+ | Connect to MCP servers | `google_trends_mcp.py`, `chat.py` |
| `fastapi` | latest | Web framework | `main.py`, all routers |
| `sse-starlette` | latest | Server-Sent Events | `chat.py` → `EventSourceResponse` |
| `supabase` | latest | Auth + Database | `supabase.py`, `auth.py` |
| `tavily-python` | latest | Web search API | Used internally by LangChain |

---

## Summary

```
User types message
  → Frontend sends POST /chat/send with JWT
    → Auth middleware verifies JWT
      → Save user message to Supabase
        → Load MCP tools from Docker container
          → Load chat history from Supabase (memory)
            → Create ReAct agent (LLM + Tools + Prompt)
              → Agent thinks: "Should I use a tool?"
                → YES: calls tool → reads result → thinks again
                → NO: generates final answer
              → Streams tokens back via SSE
            → Frontend shows tokens one by one (typing effect)
          → Save assistant response to Supabase
        → Done!
```

**The ReAct pattern is what makes this more than a simple chatbot — it can REASON about when to use tools and ACT on them autonomously.**
