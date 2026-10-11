import os
import pytest
import sys

PLUGIN_DIR = r"C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard"
sys.path.insert(0, PLUGIN_DIR)

from __init__ import (
    _on_pre_tool_call,
    check_worker_tool_gate,
    _update_session_state,
    _PARENT_SESSION_CACHE,
    _WORKER_SCOPES,
)


@pytest.fixture(autouse=True)
def cleanup_env():
    os.environ.pop("TAADAA_WORKER", None)
    _PARENT_SESSION_CACHE.clear()
    _WORKER_SCOPES.clear()
    yield


def test_bypass_1_worker_terminal_shell_redirection_blocked():
    """BYPASS 1: Worker dùng terminal redirect '> file.py' hoặc Set-Content -> BỊ CHẶN."""
    worker_sid = "worker_bypass_1"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    cmd = "echo 'bad' > D:/Taadaa/automation-core/src/automation_core/startup.py"
    res = check_worker_tool_gate("terminal", worker_sid, {"command": cmd})
    assert res is not None
    assert res.get("action") == "block"
    assert "SHELL FILE WRITE BLOCKED" in res.get("reason", "")


def test_bypass_1_worker_execute_code_file_write_blocked():
    """BYPASS 1: Worker dùng execute_code có open(..., 'w') để ghi file ngầm -> BỊ CHẶN."""
    worker_sid = "worker_bypass_1b"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1b"

    code = "with open('D:/Taadaa/test.py', 'w') as f: f.write('bad')"
    res = check_worker_tool_gate("execute_code", worker_sid, {"code": code})
    assert res is not None
    assert res.get("action") == "block"
    assert "EXECUTE CODE FILE WRITE BLOCKED" in res.get("reason", "")


def test_bypass_2_non_code_worker_is_read_only():
    """BYPASS 2: Worker từ task non_code (target_files=[]) cố ghi file -> BỊ CHẶN READ-ONLY."""
    parent_sid = "parent_non_code"
    worker_sid = "worker_non_code"
    _PARENT_SESSION_CACHE[worker_sid] = parent_sid
    _update_session_state(parent_sid, {"target_files": []})

    res = check_worker_tool_gate("write_file", worker_sid, {"path": "D:/Taadaa/automation-core/README.md"})
    assert res is not None
    assert res.get("action") == "block"
    assert "READ-ONLY WORKER" in res.get("reason", "")


def test_bypass_4_coordinator_direct_write_guard_source_blocked():
    """BYPASS 4: Coordinator ở phase IDLE cố ghi đè mã nguồn của plugin guard -> BỊ CHẶN SELF-PROTECTION."""
    coord_sid = "coord_idle_session"
    _update_session_state(coord_sid, {"phase": "IDLE", "build_token": False})

    guard_path = r"C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard/__init__.py"
    res = _on_pre_tool_call("write_file", {"path": guard_path, "content": "# hacked"}, session_id=coord_sid)
    assert res is not None
    assert res.get("action") == "block"
    assert "GUARD SELF-PROTECTION" in res.get("reason", "")


def test_bypass_5_worker_out_of_whitelist_blocked():
    """BYPASS 5: Worker cố ghi file ra ngoài whitelist (C:/Windows/...) -> BỊ CHẶN OUT OF WHITELIST."""
    worker_sid = "worker_wlist"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_wlist"

    res = check_worker_tool_gate("write_file", worker_sid, {"path": "C:/Windows/System32/drivers/etc/hosts"})
    assert res is not None
    assert res.get("action") == "block"
    assert "OUT OF WHITELIST" in res.get("reason", "")


def test_bypass_6_unrelated_test_file_blocked():
    """BYPASS 6: Worker cố ghi file test lạ không khớp stem của target file -> BỊ CHẶN SCOPE LOCK BREACH."""
    parent_sid = "parent_p6"
    worker_sid = "worker_p6"
    _PARENT_SESSION_CACHE[worker_sid] = parent_sid

    target = r"D:/Taadaa/automation-core/src/automation_core/startup.py"
    _update_session_state(parent_sid, {"target_files": [target]})

    # Ghi test_random_payload.py (không khớp startup) -> BỊ CHẶN!
    res = check_worker_tool_gate("patch", worker_sid, {"path": "D:/Taadaa/automation-core/src/automation_core/test_random_payload.py"})
    assert res is not None
    assert res.get("action") == "block"
    assert "SCOPE LOCK BREACH" in res.get("reason", "")


def test_happy_path_exact_target_and_exact_test_allowed():
    """Happy path: Worker ghi đúng file target và đúng test_<stem>.py -> CHO PHÉP."""
    parent_sid = "parent_happy"
    worker_sid = "worker_happy"
    _PARENT_SESSION_CACHE[worker_sid] = parent_sid

    target = r"D:/Taadaa/automation-core/src/automation_core/startup.py"
    _update_session_state(parent_sid, {"target_files": [target]})

    # 1. Đúng target file
    res1 = check_worker_tool_gate("patch", worker_sid, {"path": target})
    assert res1 is None

    # 2. Đúng test_<stem>.py
    exact_test = r"D:/Taadaa/automation-core/src/automation_core/test_startup.py"
    res2 = check_worker_tool_gate("write_file", worker_sid, {"path": exact_test})
    assert res2 is None
