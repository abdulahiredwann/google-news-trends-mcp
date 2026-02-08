"""
supabase.py — Supabase Database Service (Messages & Conversations)
==================================================================

Handles all database operations for chat messages stored in Supabase PostgreSQL.

Key concepts:
    - We use Supabase's Python client to interact with the `messages` table.
    - Row Level Security (RLS) is enabled: users can only read/write their own messages.
    - To make RLS work, we pass the user's JWT access_token to the Supabase client
      via `client.postgrest.auth(token)`. This tells Supabase "this request is from
      user X" so the RLS policies (auth.uid() = user_id) are enforced.

Functions:
    get_supabase_client()  → Create a Supabase client (with optional JWT for RLS)
    save_message()         → Insert a new message into the messages table
    get_messages()         → Fetch all messages in a conversation (chronological)
    get_conversations()    → List all conversations for a user (with titles)

Database schema (messages table):
    id              UUID        Primary key (auto-generated)
    user_id         UUID        References auth.users(id)
    conversation_id TEXT        Groups messages into conversations
    role            TEXT        'user', 'assistant', or 'system'
    content         TEXT        The message text
    created_at      TIMESTAMPTZ Auto-set to now()
"""

from supabase import create_client, Client
from app.core.config import settings
from typing import Optional
import uuid


def get_supabase_client(access_token: Optional[str] = None) -> Client:
    """
    Create a Supabase client instance.

    Args:
        access_token (Optional[str]): The user's JWT token from Supabase Auth.
            If provided, it's set on the PostgREST client so that Row Level
            Security (RLS) policies can identify the authenticated user.
            If None, the client uses only the anon key (limited by RLS).

    Returns:
        Client: A configured Supabase client ready for database operations.

    Why we pass the access_token:
        Supabase RLS policies use `auth.uid()` to check which user is making
        the request. The anon key alone doesn't carry user identity. By calling
        `client.postgrest.auth(token)`, we tell PostgREST "this is user X",
        and the RLS policy `user_id = auth.uid()` can then match correctly.
    """
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    if access_token:
        client.postgrest.auth(access_token)
    return client


# ══════════════════════════════════════════════════════════════════════════════
# Messages CRUD
# ══════════════════════════════════════════════════════════════════════════════

def save_message(
    conversation_id: str,
    user_id: str,
    role: str,
    content: str,
    access_token: str = "",
) -> dict:
    """
    Save a chat message to the Supabase `messages` table.

    Called twice per chat exchange:
        1. When the user sends a message (role="user")
        2. When the AI finishes responding (role="assistant")

    Args:
        conversation_id (str): UUID grouping messages into a conversation.
        user_id         (str): UUID of the authenticated user.
        role            (str): "user" or "assistant" (or "system" for system prompts).
        content         (str): The message text.
        access_token    (str): User's JWT for RLS authentication.

    Returns:
        dict: The saved message row from the database.

    RLS:
        The `insert_own_messages` policy ensures `user_id = auth.uid()`.
        If the token doesn't match, Supabase rejects the insert with a
        "row-level security policy" error.
    """
    client = get_supabase_client(access_token)
    data = {
        "id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "user_id": user_id,
        "role": role,
        "content": content,
    }
    result = client.table("messages").insert(data).execute()
    return result.data[0] if result.data else data


def get_messages(conversation_id: str, user_id: str, access_token: str = "") -> list[dict]:
    """
    Fetch all messages in a conversation, ordered chronologically.

    Used by:
        - GET /chat/conversations/{id}/messages (frontend loads chat history)
        - ReAct agent (loads conversation history before generating a response)

    Args:
        conversation_id (str): UUID of the conversation to fetch.
        user_id         (str): UUID of the user (for the query filter).
        access_token    (str): User's JWT for RLS authentication.

    Returns:
        list[dict]: Messages ordered by created_at ascending (oldest first).
            Each dict has: id, conversation_id, user_id, role, content, created_at.

    Security:
        Double protection:
        1. RLS policy: `user_id = auth.uid()` (database level)
        2. .eq("user_id", user_id) filter (application level)
    """
    client = get_supabase_client(access_token)
    result = (
        client.table("messages")
        .select("*")
        .eq("conversation_id", conversation_id)
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
    )
    return result.data or []


def get_conversations(user_id: str, access_token: str = "") -> list[dict]:
    """
    List all conversations for a user, with titles and timestamps.

    Since we don't have a separate `conversations` table, we derive
    conversations from the `messages` table by grouping on conversation_id.

    Title logic:
        The title is the first user message in the conversation, truncated
        to 60 characters. If no user message exists yet, the title is "New Chat".

    Args:
        user_id      (str): UUID of the user.
        access_token (str): User's JWT for RLS authentication.

    Returns:
        list[dict]: Conversations sorted by most recent activity (newest first).
            Each dict has: id, title, created_at, updated_at.

    Algorithm:
        1. Fetch ALL messages for this user, ordered by created_at.
        2. Iterate through messages, grouping by conversation_id.
        3. For each group, track the first user message (→ title) and
           the latest message timestamp (→ updated_at).
        4. Sort by updated_at descending (most recent first).
    """
    client = get_supabase_client(access_token)
    result = (
        client.table("messages")
        .select("conversation_id, role, content, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
    )

    # Group by conversation_id — build conversation summaries
    seen: dict[str, dict] = {}
    for msg in (result.data or []):
        cid = msg["conversation_id"]
        if cid not in seen:
            seen[cid] = {
                "id": cid,
                "title": "New Chat",
                "created_at": msg["created_at"],
                "updated_at": msg["created_at"],
            }
        # Use the first user message as the conversation title
        if msg["role"] == "user" and seen[cid]["title"] == "New Chat":
            title = msg["content"][:60]
            if len(msg["content"]) > 60:
                title += "..."
            seen[cid]["title"] = title
        # Track the latest message time for sorting
        seen[cid]["updated_at"] = msg["created_at"]

    # Sort conversations by most recent activity
    conversations = list(seen.values())
    conversations.sort(key=lambda c: c["updated_at"], reverse=True)
    return conversations
