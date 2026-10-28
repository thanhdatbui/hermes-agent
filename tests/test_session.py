import types
import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

import pytest

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from gateway.session import SessionStore


class TestSessionResumePreserver(unittest.TestCase):
    def test_last_turn_was_interrupted_user_tool(self):
        store = SessionStore.__new__(SessionStore)
        db_mock = MagicMock()
        store._db = db_mock

        # Case 1: last message is user -> True
        db_mock._lock = MagicMock()
        db_mock._conn.execute.return_value.fetchone.return_value = ("user", None)
        self.assertTrue(store._last_turn_was_interrupted("test-sess"))

        # Case 2: last message is tool -> True
        db_mock._conn.execute.return_value.fetchone.return_value = ("tool", None)
        self.assertTrue(store._last_turn_was_interrupted("test-sess"))

        # Case 3: last message is assistant without tool calls -> False
        db_mock._conn.execute.return_value.fetchone.return_value = ("assistant", None)
        self.assertFalse(store._last_turn_was_interrupted("test-sess"))

        # Case 4: last message is assistant with tool calls -> True
        db_mock._conn.execute.return_value.fetchone.return_value = ("assistant", '[{"id": "call_1"}]')
        self.assertTrue(store._last_turn_was_interrupted("test-sess"))

        # Case 5: last message is assistant with empty tool calls list -> False
        db_mock._conn.execute.return_value.fetchone.return_value = ("assistant", '[]')
        self.assertFalse(store._last_turn_was_interrupted("test-sess"))

    def test_suspend_recently_active_filters(self):
        store = SessionStore.__new__(SessionStore)
        import threading
        from datetime import datetime, timedelta
        store._lock = threading.Lock()
        store._loaded = True
        store._entries = {}
        now_dt = datetime(2026, 10, 13, 12, 0, 0)
        entry_old = MagicMock(session_id="s_old", updated_at=now_dt - timedelta(seconds=3600), resume_pending=False, suspended=False)
        entry_active = MagicMock(session_id="s_active", updated_at=now_dt - timedelta(seconds=600), resume_pending=False, suspended=False)
        entry_done = MagicMock(session_id="s_done", updated_at=now_dt - timedelta(seconds=600), resume_pending=False, suspended=False)
        store._entries = {
            "s_old": entry_old,
            "s_active": entry_active,
            "s_done": entry_done,
        }
        store._last_turn_was_interrupted = MagicMock(side_effect=lambda s: s == "s_active")
        store._save = MagicMock()
        with patch("gateway.session._now", return_value=now_dt):
            count = store.suspend_recently_active(max_age_seconds=1800)
        self.assertEqual(count, 1)
        self.assertTrue(entry_active.resume_pending)
        self.assertFalse(entry_old.resume_pending)
        self.assertFalse(entry_done.resume_pending)

    def test_last_turn_was_interrupted_real_sessiondb(self):
        import tempfile
        from hermes_state import SessionDB

        with tempfile.TemporaryDirectory() as tmp:
            db = SessionDB(db_path=Path(tmp) / "state.db")
            try:
                store = SessionStore.__new__(SessionStore)
                store._db = db

                # Unknown session / no messages -> False
                db.create_session("empty", "telegram")
                self.assertFalse(store._last_turn_was_interrupted("empty"))
                self.assertFalse(store._last_turn_was_interrupted(""))

                # Last message is user -> interrupted
                db.create_session("s_user", "telegram")
                db.append_message("s_user", "user", "hello")
                self.assertTrue(store._last_turn_was_interrupted("s_user"))

                # Assistant finished replying -> not interrupted
                db.append_message("s_user", "assistant", "hi there")
                self.assertFalse(store._last_turn_was_interrupted("s_user"))

                # Assistant issued tool_calls without result -> interrupted
                db.create_session("s_tool", "telegram")
                db.append_message("s_tool", "user", "run it")
                db.append_message(
                    "s_tool",
                    "assistant",
                    None,
                    tool_calls=[{"id": "call_1", "type": "function",
                                 "function": {"name": "terminal", "arguments": "{}"}}],
                )
                self.assertTrue(store._last_turn_was_interrupted("s_tool"))

                # Tool result is last -> interrupted
                db.append_message(
                    "s_tool", "tool", "done", tool_name="terminal", tool_call_id="call_1"
                )
                self.assertTrue(store._last_turn_was_interrupted("s_tool"))

                # Final assistant reply after the tool result -> not interrupted
                db.append_message("s_tool", "assistant", "all done")
                self.assertFalse(store._last_turn_was_interrupted("s_tool"))
            finally:
                db.close()


class _CapturingAgent:
    captured_message = None

    def __init__(self, *args, **kwargs):
        self.tools = []

    def run_conversation(self, user_message, conversation_history=None, task_id=None, persist_user_message=None):
        type(self).captured_message = user_message
        return {"final_response": "ok", "messages": [], "api_calls": 1, "completed": True}


@pytest.mark.asyncio
async def test_auto_continue_resume_system_note_guards(monkeypatch, tmp_path):
    import threading
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    import gateway.run as gateway_run
    import hermes_cli.tools_config as tools_config
    from gateway.config import Platform
    from gateway.session import SessionSource

    fake_run_agent = types.ModuleType("run_agent")
    fake_run_agent.AIAgent = _CapturingAgent
    monkeypatch.setitem(sys.modules, "run_agent", fake_run_agent)
    monkeypatch.setattr(gateway_run, "_hermes_home", tmp_path)
    monkeypatch.setattr(gateway_run, "_env_path", tmp_path / ".env")
    monkeypatch.setattr(gateway_run, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(gateway_run, "_load_gateway_config", lambda: {})
    monkeypatch.setattr(gateway_run, "_resolve_gateway_model", lambda config=None: "gpt-5.4")
    monkeypatch.setattr(
        gateway_run,
        "_resolve_runtime_agent_kwargs",
        lambda: {
            "provider": "openrouter",
            "api_mode": "chat_completions",
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": "***",
        },
    )
    monkeypatch.setattr(tools_config, "_get_platform_tools", lambda user_config, platform_key: {"core"})

    session_key = "agent:main:telegram:dm:1"
    resume_entry = SimpleNamespace(
        resume_pending=True,
        resume_reason="restart_interrupted",
        last_resume_marked_at=None,
    )
    runner = object.__new__(gateway_run.GatewayRunner)
    runner.adapters = {}
    runner._ephemeral_system_prompt = ""
    runner._prefill_messages = []
    runner._reasoning_config = None
    runner._service_tier = None
    runner._provider_routing = {}
    runner._fallback_model = None
    runner._running_agents = {}
    runner._pending_model_notes = {}
    runner._session_db = None
    runner._agent_cache = {}
    runner._agent_cache_lock = threading.Lock()
    runner._session_model_overrides = {}
    runner.hooks = SimpleNamespace(loaded_hooks=False)
    runner.config = SimpleNamespace(streaming=None)
    runner.session_store = SimpleNamespace(
        _entries={session_key: resume_entry},
        get_or_create_session=lambda source: SimpleNamespace(session_id="session-1"),
        load_transcript=lambda session_id: [],
    )
    runner._get_or_create_gateway_honcho = lambda key: (None, None)
    runner._enrich_message_with_vision = AsyncMock(return_value="")

    _CapturingAgent.captured_message = None
    await runner._run_agent(
        message="",
        context_prompt="",
        history=[],
        source=SessionSource(platform=Platform.TELEGRAM, chat_id="1", chat_type="dm", user_id="u1"),
        session_id="session-1",
        session_key=session_key,
    )

    note = _CapturingAgent.captured_message
    assert note.startswith("[System note:") and note.endswith("]")
    assert "a PC reboot or unexpected gateway exit" in note
    assert "Kiểm tra lại hiện trường" in note
    assert "Do NOT replay old tool calls" in note
    assert "NEVER re-run any reboot/shutdown/restart command" in note
    assert "Do NOT take irreversible actions on accounts/devices until the device lock is verified" in note
    assert "BLOCKED" in note

    # Case B: message contains only user tag prefix like in forum topic
    _CapturingAgent.captured_message = None
    await runner._run_agent(
        message="[Tad Shavershian]   ",
        context_prompt="",
        history=[],
        source=SessionSource(platform=Platform.TELEGRAM, chat_id="1", chat_type="group", thread_id="123", user_id="u1"),
        session_id="session-1",
        session_key=session_key,
    )
    note_tagged = _CapturingAgent.captured_message
    assert "Kiểm tra lại hiện trường" in note_tagged
    assert "Address the user's NEW message" not in note_tagged

    # Case C: message contains real user text -> addresses user message
    _CapturingAgent.captured_message = None
    await runner._run_agent(
        message="[Tad Shavershian] Lam tiep cho tao",
        context_prompt="",
        history=[],
        source=SessionSource(platform=Platform.TELEGRAM, chat_id="1", chat_type="group", thread_id="123", user_id="u1"),
        session_id="session-1",
        session_key=session_key,
    )
    note_real = _CapturingAgent.captured_message
    assert "Address the user's NEW message below FIRST" in note_real
    assert "Lam tiep cho tao" in note_real

    # Case D: restart_timeout reason
    resume_entry.resume_reason = "restart_timeout"
    _CapturingAgent.captured_message = None
    await runner._run_agent(
        message="",
        context_prompt="",
        history=[],
        source=SessionSource(platform=Platform.TELEGRAM, chat_id="1", chat_type="dm", user_id="u1"),
        session_id="session-1",
        session_key=session_key,
    )
    note_restart = _CapturingAgent.captured_message
    assert "a gateway restart" in note_restart
    assert "Kiểm tra lại hiện trường" in note_restart


if __name__ == "__main__":
    unittest.main()

