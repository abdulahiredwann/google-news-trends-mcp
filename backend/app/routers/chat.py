"""
chat.py — Chat Router (Conversations, Messages, AI Streaming)
=============================================================

This is the main router for the chat feature. It handles:

Endpoints:
    GET  /chat/conversations                       → List all conversations for the user
    GET  /chat/conversations/{conversation_id}/messages → Get messages in a conversation
    POST /chat/send                                → Send a message & stream AI response via SSE

All endpoints are PROTECTED — the AuthMiddleware validates the JWT token
and attaches user_id + access_token to request.state before these handlers run.

SSE (Server-Sent Events) Streaming:
    The /chat/send endpoint returns an EventSourceResponse that streams events:
    - "token"       → A chunk of the AI's response text (arrives incrementally)
    - "tool_start"  → The agent started using a tool (e.g. "tavily_search")
    - "tool_end"    → The agent finished using a tool
    - "tool_status" → Informational message (e.g. "MCP unavailable")
    - "done"        → Final event with the conversation_id

    The frontend reads these events to show:
    - Tokens appearing one by one (streaming effect)
    - "Using tavily_search..." indicator
    - The conversation_id for future reference
"""

import json
import uuid
import traceback
import logging
from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

from sse_starlette.sse import EventSourceResponse
from app.schemas.chat import ChatRequest, MessageOut, ConversationOut
from app.services.db.supabase import (
    get_conversations,
    get_messages,
    save_message,
)
from app.services.agent.react_agent import run_agent_stream
from app.services.tools.google_trends_mcp import get_mcp_client_config
from langchain_mcp_adapters.client import MultiServerMCPClient

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(request: Request):
    """
    List all conversations for the authenticated user.

    Reads user_id and access_token from request.state (set by AuthMiddleware).
    Queries the messages table, groups by conversation_id, and returns a list
    of conversations with titles derived from the first user message.

    Args:
        request (Request): FastAPI request with state.user_id and state.access_token.

    Returns:
        list[ConversationOut]: Conversations sorted by most recent activity.
            Each has: id, title, created_at, updated_at.
    """
    user_id = request.state.user_id
    token = request.state.access_token
    conversations = get_conversations(user_id, access_token=token)
    return conversations


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(conversation_id: str, request: Request):
    """
    Get all messages in a specific conversation.

    Returns messages ordered by created_at (oldest first) so the frontend
    can display them in chronological order.

    Args:
        conversation_id (str): UUID of the conversation.
        request (Request): FastAPI request with state.user_id and state.access_token.

    Returns:
        list[MessageOut]: Messages with id, conversation_id, user_id, role, content, created_at.

    Security:
        RLS policy + user_id filter ensures users can only see their own messages.
    """
    user_id = request.state.user_id
    token = request.state.access_token
    messages = get_messages(conversation_id, user_id, access_token=token)
    return messages


@router.post("/send")
async def send_message(req: ChatRequest, request: Request):
    """
    Send a user message and stream the AI response via Server-Sent Events (SSE).

    This is the core endpoint that ties everything together:
    1. Saves the user's message to Supabase.
    2. Loads MCP tools from the Google Trends MCP server (gracefully skips if down).
    3. Runs the LangChain ReAct agent with the user's message + chat history.
    4. Streams the agent's response tokens and tool activity events to the frontend.
    5. Saves the complete AI response to Supabase.
    6. Sends a final "done" event with the conversation_id.

    Args:
        req (ChatRequest): JSON body with `message` (string) and optional `conversation_id`.
        request (Request): FastAPI request with state.user_id and state.access_token.

    Returns:
        EventSourceResponse: SSE stream with events:
            - "token": {"content": "partial text"}
            - "tool_start": {"tool": "tavily_search"}
            - "tool_end": {"tool": "tavily_search"}
            - "tool_status": {"type": "info", "message": "..."}
            - "done": {"conversation_id": "uuid"}
    """
    user_id = request.state.user_id
    token = request.state.access_token

    # Generate a new conversation_id if this is a new chat
    conversation_id = req.conversation_id or str(uuid.uuid4())

    # ── Step 1: Save the user's message to Supabase ────────────────────────
    save_message(
        conversation_id=conversation_id,
        user_id=user_id,
        role="user",
        content=req.message,
        access_token=token,
    )

    async def event_generator():
        """
        Async generator that yields SSE events as the AI agent processes the message.

        This generator:
        - Attempts to load MCP tools (Google Trends) — skips if unavailable
        - Runs the ReAct agent which may call tools and stream tokens
        - Catches errors and returns user-friendly error messages
        - Saves the final assistant response to the database
        - Sends a "done" event to signal the stream is complete
        """
        full_response = ""
        try:
            # ── Load MCP tools (Google Trends) ─────────────────────────────
            # If the MCP server is down, we gracefully continue without those
            # tools. The agent still has Tavily + its own knowledge.
            mcp_tools = []
            try:
                config = get_mcp_client_config(access_token=token)
                mcp_client = MultiServerMCPClient(config)
                mcp_tools = await mcp_client.get_tools()
                logger.info(f"MCP tools loaded: {[t.name for t in mcp_tools]}")
            except Exception as mcp_err:
                # MCP server unavailable — log the error but don't crash
                logger.error(f"MCP connection error: {mcp_err}")
                logger.error(traceback.format_exc())
                yield {
                    "event": "tool_status",
                    "data": json.dumps({"type": "info", "message": "Google Trends MCP unavailable, continuing without it"}),
                }

            # ── Stream the ReAct agent's response ──────────────────────────
            # The agent decides which tools to use (if any), calls them,
            # reasons about the results, and generates a response — all streamed.
            async for event in run_agent_stream(
                user_message=req.message,
                conversation_id=conversation_id,
                user_id=user_id,
                access_token=token,
                mcp_tools=mcp_tools,
            ):
                event_type = event["type"]

                if event_type == "token":
                    # A chunk of the AI's text response
                    full_response += event["content"]
                    yield {
                        "event": "token",
                        "data": json.dumps({"content": event["content"]}),
                    }

                elif event_type == "tool_start":
                    # Agent started using a tool (e.g. "tavily_search")
                    yield {
                        "event": "tool_start",
                        "data": json.dumps({"tool": event["tool"]}),
                    }

                elif event_type == "tool_end":
                    # Agent finished using a tool
                    yield {
                        "event": "tool_end",
                        "data": json.dumps({"tool": event["tool"]}),
                    }

                elif event_type == "done":
                    # Agent completed — capture the full response
                    full_response = event["content"]

        except ValueError as e:
            # Missing API key (e.g. OPENAI_API_KEY not set)
            full_response = f"Configuration error: {str(e)}. Please set your API keys in the backend .env file."
            yield {
                "event": "token",
                "data": json.dumps({"content": full_response}),
            }

        except Exception:
            # Unexpected error — return a friendly message, don't leak internals
            full_response = "Sorry, something went wrong processing your request. Please try again."
            yield {
                "event": "token",
                "data": json.dumps({"content": full_response}),
            }

        # ── Save the assistant's response to Supabase ──────────────────────
        if full_response:
            save_message(
                conversation_id=conversation_id,
                user_id=user_id,
                role="assistant",
                content=full_response,
                access_token=token,
            )

        # ── Send the final "done" event ────────────────────────────────────
        # This tells the frontend the stream is complete and provides the
        # conversation_id (important for new chats that didn't have one yet).
        yield {
            "event": "done",
            "data": json.dumps({"conversation_id": conversation_id}),
        }

    return EventSourceResponse(event_generator())
