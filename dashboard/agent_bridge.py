"""
Thin adapter between the Streamlit dashboard and the agentic ai layer's
LangGraph agent. Keeps graph/state details out of dashboard/app.py.

Also persists chat turns to the project's existing agent memory database
(database/memory/agent_memory.db) so the dashboard's chat history reflects
real conversations instead of placeholder text.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from graph.workflows import run as run_agent
from database.memory.memory_queries import (
    create_session,
    save_message,
    get_conversation,
    list_sessions,
)

HISTORY_TITLE_MAX_LEN = 40


def ask_agent(user_request: str, session_id: str) -> str:
    """
    Send a user request through the real agent graph, persist both sides
    of the exchange to the memory database, and return a single string
    suitable for display in the chat panel.

    Auto-approves any human-in-the-loop interrupts (auto_approve=True) so
    the dashboard chat never blocks on a terminal input() prompt. Revisit
    this if the dashboard should surface approval steps to the user
    instead of auto-approving them.
    """
    try:
        state = run_agent(user_request, auto_approve=True)
        response = state.get("final_response") or "The agent did not return a response."
    except Exception as exc:
        response = f"Sorry, the agent hit an error handling that request: {exc}"

    save_message(session_id, "user", user_request)
    save_message(session_id, "assistant", response)

    return response


def new_session() -> str:
    """Start a new persisted chat session and return its session_id."""
    return create_session()


def get_history(session_id: str) -> list[dict]:
    """
    Return the real message history for a session as a list of
    {"role", "content"} dicts, oldest first, ready for st.chat_message.
    """
    return [
        {"role": message["sender"], "content": message["message"]}
        for message in get_conversation(session_id)
    ]


def list_chat_sessions(limit: int = 10) -> list[dict]:
    """
    Return recent chat sessions that actually contain messages, most
    recent first, each with a display title derived from its first
    user message.
    """
    chats = []
    for session in list_sessions():
        session_id = session["session_id"]
        messages = get_conversation(session_id)
        first_user_message = next(
            (m["message"] for m in messages if m["sender"] == "user"), None
        )
        if not first_user_message:
            continue

        title = first_user_message.strip()
        if len(title) > HISTORY_TITLE_MAX_LEN:
            title = title[: HISTORY_TITLE_MAX_LEN - 3] + "..."

        chats.append({"session_id": session_id, "title": title})
        if len(chats) >= limit:
            break

    return chats
