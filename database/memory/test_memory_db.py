from database.memory.init_memory_db import init_memory_db
from database.memory.memory_queries import (
    create_session,
    end_session,
    get_conversation,
    get_session_history,
    list_sessions,
    save_agent_output,
    save_log,
    save_message,
    save_tool_call,
)


def test_init_memory_db_creates_expected_tables(tmp_path):
    db_path = tmp_path / "agent_memory.db"
    init_memory_db(db_path)

    import sqlite3

    with sqlite3.connect(db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"sessions", "messages", "agent_outputs", "tool_calls", "execution_logs"} <= tables


def test_create_session_and_end_session(tmp_path):
    db_path = tmp_path / "agent_memory.db"
    init_memory_db(db_path)

    session_id = create_session(user_id="tester", db_path=db_path)
    sessions = list_sessions(db_path=db_path)
    assert sessions[0]["session_id"] == session_id
    assert sessions[0]["status"] == "active"

    end_session(session_id, status="completed", db_path=db_path)
    sessions = list_sessions(db_path=db_path)
    assert sessions[0]["status"] == "completed"
    assert sessions[0]["ended_at"] is not None


def test_save_and_get_conversation(tmp_path):
    db_path = tmp_path / "agent_memory.db"
    init_memory_db(db_path)
    session_id = create_session(db_path=db_path)

    save_message(session_id, "user", "turn off the lights", db_path=db_path)
    save_message(session_id, "assistant", "done", db_path=db_path)

    conversation = get_conversation(session_id, db_path=db_path)
    assert [m["sender"] for m in conversation] == ["user", "assistant"]


def test_get_session_history_aggregates_everything(tmp_path):
    db_path = tmp_path / "agent_memory.db"
    init_memory_db(db_path)
    session_id = create_session(user_id="tester", db_path=db_path)

    save_message(session_id, "user", "status?", db_path=db_path)
    save_agent_output(session_id, "bms", {"status": "ok"}, db_path=db_path)
    save_tool_call(session_id, "bms_write", {"target": "hvac"}, {"ack": True}, db_path=db_path)
    save_log(session_id, "bms: executed 1 action(s)", db_path=db_path)

    history = get_session_history(session_id, db_path=db_path)
    assert history["session"]["user_id"] == "tester"
    assert len(history["messages"]) == 1
    assert len(history["agent_outputs"]) == 1
    assert len(history["tool_calls"]) == 1
    assert history["tool_calls"][0]["arguments"] == {"target": "hvac"}
    assert len(history["execution_logs"]) == 1


def test_get_session_history_for_unknown_session_returns_none_session(tmp_path):
    db_path = tmp_path / "agent_memory.db"
    init_memory_db(db_path)

    history = get_session_history("does-not-exist", db_path=db_path)
    assert history["session"] is None
    assert history["messages"] == []
