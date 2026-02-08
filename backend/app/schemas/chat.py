"""
chat.py — Chat Pydantic Schemas
================================

Defines the request/response models for the chat endpoints.

Models:
    ChatRequest     → Input for POST /chat/send
    MessageOut      → A single message in a conversation (used in GET messages)
    ConversationOut → A conversation summary (used in GET conversations)
"""

from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    """
    Request body for sending a chat message.

    Fields:
        message         (str):           The user's message text.
        conversation_id (Optional[str]): UUID of an existing conversation.
                                         If None, the backend creates a new conversation.

    Example JSON (new conversation):
        { "message": "Hello, what can you do?" }

    Example JSON (existing conversation):
        { "message": "Tell me more", "conversation_id": "668c3916-..." }
    """
    message: str
    conversation_id: Optional[str] = None


class MessageOut(BaseModel):
    """
    A single message returned from the database.

    Fields:
        id              (str): UUID of the message (from Supabase).
        conversation_id (str): UUID grouping messages into a conversation.
        user_id         (str): UUID of the user who owns this message.
        role            (str): "user", "assistant", or "system".
        content         (str): The message text.
        created_at      (str): ISO 8601 timestamp (e.g. "2026-02-08T10:30:00Z").

    Used by:
        GET /chat/conversations/{id}/messages
    """
    id: str
    conversation_id: str
    user_id: str
    role: str
    content: str
    created_at: str


class ConversationOut(BaseModel):
    """
    A conversation summary returned in the conversations list.

    Fields:
        id         (str): The conversation_id (UUID).
        title      (str): Derived from the first user message (truncated to 60 chars).
        created_at (str): Timestamp of the first message in the conversation.
        updated_at (str): Timestamp of the most recent message.

    Used by:
        GET /chat/conversations
    """
    id: str
    title: str
    created_at: str
    updated_at: str
