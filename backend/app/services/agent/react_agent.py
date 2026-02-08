"""
react_agent.py — LangChain ReAct Agent (Reasoning + Acting)
============================================================

This is the brain of the AI chat agent. It implements the ReAct pattern:
    1. REASON: The LLM thinks about what to do (use a tool? answer directly?)
    2. ACT:    If a tool is needed, the agent calls it and observes the result.
    3. REPEAT: The agent can reason → act → observe multiple times.
    4. RESPOND: Finally, the agent generates a natural language response.

Architecture:
    ┌──────────────┐     ┌─────────────────┐     ┌──────────────────────┐
    │  User Message │ →  │  ReAct Agent     │ →  │  Streaming Response   │
    │  + History    │     │  (GPT-4o-mini)  │     │  (tokens + tool events│
    └──────────────┘     │                  │     └──────────────────────┘
                         │  Tools:          │
                         │  - Tavily Search │
                         │  - MCP Tools     │
                         │    (Google News) │
                         └─────────────────┘

How the agent decides which tool to use:
    - The SYSTEM_PROMPT tells the agent its capabilities and guidelines.
    - Each tool has a `description` that the LLM reads.
    - Based on the user's message, the LLM decides:
      → "Search the web" → uses tavily_search
      → "Google Trends"  → uses an MCP tool (e.g. get_trending_terms)
      → General question  → answers from its own knowledge (no tool call)

Functions:
    build_chat_history()  → Convert DB messages to LangChain message objects
    get_llm()             → Create the ChatOpenAI LLM instance
    create_agent()        → Build the ReAct agent with tools
    run_agent_stream()    → Execute the agent and yield streaming events
"""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.core.config import settings
from app.services.tools.tavily import get_tavily_tool
from app.services.db.supabase import get_messages
import os


# ══════════════════════════════════════════════════════════════════════════════
# System Prompt — Instructions for the AI agent
# ══════════════════════════════════════════════════════════════════════════════
# This prompt is prepended to every conversation. It tells the LLM:
#   - What tools it has access to
#   - When to use each tool
#   - How to format its responses
SYSTEM_PROMPT = """You are a helpful AI assistant with access to tools.
You can search the web using Tavily and check Google Trends/News using the MCP tools.

Guidelines:
- Use tavily_search when the user wants to find information on the web or about recent events.
- Use Google Trends MCP tools when the user asks about trending topics, Google Trends data, or Google News.
- If the user asks a general knowledge question, answer from your own knowledge without using tools.
- Always provide clear, concise, and helpful responses.
- When using tool results, summarize them naturally — don't just dump raw data.
"""


def build_chat_history(messages: list[dict]) -> list:
    """
    Convert stored database messages into LangChain message objects.

    LangChain expects messages as typed objects (HumanMessage, AIMessage,
    SystemMessage), not plain dicts. This function does the conversion.

    Args:
        messages (list[dict]): Messages from the database, each with:
            - role: "user", "assistant", or "system"
            - content: The message text

    Returns:
        list: LangChain message objects in chronological order.

    Example:
        Input:  [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi!"}]
        Output: [HumanMessage(content="Hello"), AIMessage(content="Hi!")]

    Why this matters:
        The ReAct agent uses chat history to maintain context across messages.
        For example, if the user says "My name is Fazal" in message 1, and
        asks "What's my name?" in message 3, the agent can answer correctly
        because it sees the full conversation history.
    """
    history = []
    for msg in messages:
        if msg["role"] == "user":
            history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            history.append(AIMessage(content=msg["content"]))
        elif msg["role"] == "system":
            history.append(SystemMessage(content=msg["content"]))
    return history


def get_llm():
    """
    Create the ChatOpenAI LLM instance.

    Returns:
        ChatOpenAI: Configured with:
            - model="gpt-4o-mini": Fast, cheap, good enough for tool-use tasks
            - temperature=0: Deterministic responses (no randomness)
            - streaming=True: Enables token-by-token streaming

    Raises:
        ValueError: If OPENAI_API_KEY is not set in the environment.

    Why gpt-4o-mini?
        - It supports tool calling (function calling) natively
        - It's much cheaper than gpt-4o ($0.15/1M input vs $5/1M)
        - It's fast enough for real-time chat
        - It handles ReAct reasoning well
    """
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set")
    os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
    return ChatOpenAI(model="gpt-4o-mini", temperature=0, streaming=True)


async def create_agent(mcp_tools: list = None):
    """
    Build the LangChain ReAct agent with all available tools.

    This uses LangGraph's `create_react_agent()` which automatically
    creates a graph that implements the ReAct loop:
        Reason → Act (tool call) → Observe → Reason → ... → Final Answer

    Args:
        mcp_tools (list, optional): Tools from the Google Trends MCP server.
            These are LangChain-compatible tools created by langchain-mcp-adapters.
            If the MCP server is down, this will be an empty list.

    Returns:
        CompiledGraph: A LangGraph agent ready to process messages.

    Tool priority (decided by the LLM based on the user's query):
        1. Tavily Search → for web searches, current events, factual lookups
        2. MCP Tools → for Google Trends, Google News, trending topics
        3. No tool → for general knowledge questions the LLM can answer itself
    """
    tools = []

    # Add Tavily web search tool (None if API key not set)
    tavily = get_tavily_tool()
    if tavily:
        tools.append(tavily)

    # Add Google Trends MCP tools (empty list if MCP server is down)
    if mcp_tools:
        tools.extend(mcp_tools)

    # Create the LLM
    llm = get_llm()

    # Build the ReAct agent using LangGraph
    # create_react_agent() creates a state machine:
    #   Start → LLM decides (tool call or final answer)
    #         → If tool call: execute tool → feed result back to LLM → repeat
    #         → If final answer: return response
    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )

    return agent


async def run_agent_stream(
    user_message: str,
    conversation_id: str,
    user_id: str,
    access_token: str,
    mcp_tools: list = None,
):
    """
    Run the ReAct agent and yield streaming events for SSE.

    This is the main entry point called by the /chat/send endpoint.
    It orchestrates the full flow:
        1. Load conversation history from Supabase
        2. Build LangChain message objects
        3. Create the ReAct agent with tools
        4. Stream the agent's execution, yielding events for:
           - Tool starts/ends (so frontend shows "Using tavily_search...")
           - Token chunks (so frontend shows text appearing incrementally)
           - Final complete response

    Args:
        user_message    (str):  The user's current message.
        conversation_id (str):  UUID of the conversation (for loading history).
        user_id         (str):  UUID of the user (for Supabase queries).
        access_token    (str):  User's JWT (for RLS-authenticated DB access).
        mcp_tools       (list): MCP tools to give to the agent (may be empty).

    Yields:
        dict: Event dictionaries with different types:
            {"type": "tool_start", "tool": "tavily_search"}
            {"type": "tool_end",   "tool": "tavily_search"}
            {"type": "token",      "content": "partial text chunk"}
            {"type": "done",       "content": "full response text"}

    Event flow example (user asks "Search for LangChain agents"):
        1. yield {"type": "tool_start", "tool": "tavily_search"}
        2. yield {"type": "tool_end",   "tool": "tavily_search"}
        3. yield {"type": "token",      "content": "Based on"}
        4. yield {"type": "token",      "content": " my search"}
        5. yield {"type": "token",      "content": ", LangChain..."}
        6. ... more tokens ...
        7. yield {"type": "done",       "content": "Based on my search, LangChain..."}
    """
    # ── Step 1: Load conversation history from Supabase ────────────────────
    # This gives the agent context from previous messages in this conversation.
    # Without this, the agent wouldn't remember anything from earlier messages.
    stored_messages = get_messages(conversation_id, user_id, access_token=access_token)
    chat_history = build_chat_history(stored_messages)

    # ── Step 2: Add the new user message ───────────────────────────────────
    chat_history.append(HumanMessage(content=user_message))

    # ── Step 3: Create the ReAct agent ─────────────────────────────────────
    agent = await create_agent(mcp_tools=mcp_tools)

    # ── Step 4: Stream agent execution ─────────────────────────────────────
    # astream_events() gives us granular events as the agent works:
    #   - on_tool_start: agent is about to call a tool
    #   - on_tool_end:   tool returned a result
    #   - on_chat_model_stream: LLM is generating text (token by token)
    full_response = ""

    async for event in agent.astream_events(
        {"messages": chat_history},
        version="v2",
    ):
        kind = event["event"]

        # ── Tool started ───────────────────────────────────────────────────
        # The agent decided to use a tool. Notify the frontend so it can
        # show "Using tavily_search..." or "Fetching Google Trends...".
        if kind == "on_tool_start":
            tool_name = event.get("name", "unknown")
            yield {
                "type": "tool_start",
                "tool": tool_name,
            }

        # ── Tool finished ──────────────────────────────────────────────────
        # The tool returned results. The agent will now reason about them.
        elif kind == "on_tool_end":
            tool_name = event.get("name", "unknown")
            yield {
                "type": "tool_end",
                "tool": tool_name,
            }

        # ── LLM token streaming ───────────────────────────────────────────
        # The LLM is generating its response. Each chunk is a small piece
        # of text (could be a word, part of a word, or punctuation).
        # We stream these to the frontend for a typing effect.
        elif kind == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                content = chunk.content
                if isinstance(content, str):
                    full_response += content
                    yield {
                        "type": "token",
                        "content": content,
                    }

    # ── Step 5: Yield the final complete response ──────────────────────────
    # This lets the caller know the full text for saving to the database.
    yield {
        "type": "done",
        "content": full_response,
    }
