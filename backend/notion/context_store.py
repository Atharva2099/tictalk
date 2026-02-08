"""In-memory context and conversation stores for voice agent integration."""

from typing import Any

# session_id -> context string for voice agent
context_store: dict[str, str] = {}

# session_id -> list of {"role": "user"|"assistant", "content": "..."}
conversation_store: dict[str, list[dict[str, Any]]] = {}


def get_context(session_id: str) -> str:
    """Get Notion-derived context for a session."""
    return context_store.get(session_id, "")


def set_context(session_id: str, context: str) -> None:
    """Set context for a session (called by background agent)."""
    context_store[session_id] = context


def get_conversation(session_id: str) -> list[dict[str, Any]]:
    """Get conversation history for a session."""
    return conversation_store.get(session_id, [])


def append_conversation(session_id: str, role: str, content: str) -> None:
    """Append a message to conversation history."""
    if session_id not in conversation_store:
        conversation_store[session_id] = []
    conversation_store[session_id].append({"role": role, "content": content})
