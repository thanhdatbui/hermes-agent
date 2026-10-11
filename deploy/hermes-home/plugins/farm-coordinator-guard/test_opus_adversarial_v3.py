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
    _ACTIVE_SCOPE_MAP,
)


@pytest.fixture(autouse=True)
def cleanup_env():
    os.environ.pop("TAADAA_WORKER", None)
    _PARENT_SESSION_CACHE.clear()
    _ACTIVE_SCOPE_MAP.clear()
    yield


def test_critical_1_coordinator_terminal_guard_override_blocked():
    """C-1: Coordinator ở IDLE dùng terminal redirect ghi đè guard plugin -> BỊ CHẶN TUYỆT ĐỐI."""
    coord_sid = "coord_c1"
    _update_session_state(coord_sid, {"phase": "IDLE", "build_token": False})

    cmd = "echo malicious > C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard/__init__.py"
    res = _on_pre_tool_call("terminal", {"command": cmd}, session_id=coord_sid)
    assert res is not None
    assert res.get("action") == "block"
    assert "GUARD SELF-PROTECTION" in res.get("reason", "")


def test_critical_2_coordinator_execute_code_guard_override_blocked():
    """C-2: Coordinator ở IDLE dùng execute_code ghi đè guard plugin -> BỊ CHẶN TUYỆT ĐỐI."""
    coord_sid = "coord_c2"
    _update_session_state(coord_sid, {"phase": "IDLE", "build_token": False})

    code = "with open('C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard/__init__.py', 'w') as f: f.write('bad')"
    res = _on_pre_tool_call("execute_code", {"code": code}, session_id=coord_sid)
    assert res is not None
    assert res.get("action") == "block"
    assert "GUARD SELF-PROTECTION" in res.get("reason", "")


def test_critical_3_worker_execute_code_hard_blocked():
    """C-3: Worker gọi bất kỳ lệnh execute_code nào -> ACTION LOCK BỊ CHẶN 100%."""
    worker_sid = "worker_c3"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_c3"

    res = check_worker_tool_gate("execute_code", worker_sid, {"code": "import os; print(os.listdir())"})
    assert res is not None
    assert res.get("action") == "block"
    assert "ACTION LOCK" in res.get("reason", "")


def test_critical_4_worker_terminal_file_write_or_copy_blocked():
    """C-4: Worker dùng cp/copy/mv/PowerShell trong terminal -> ACTION LOCK BỊ CHẶN 100%."""
    worker_sid = "worker_c4"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_c4"

    cmd = "cp payload.py D:/Taadaa/automation-core/src/automation_core/startup.py"
    res = check_worker_tool_gate("terminal", worker_sid, {"command": cmd})
    assert res is not None
    assert res.get("action") == "block"
    assert "ACTION LOCK" in res.get("reason", "")


def test_medium_6_env_worker_is_strictly_bound():
    """M-6: env_worker (TAADAA_WORKER=1) vẫn bị ràng buộc Whitelist & Guard Protection 100%."""
    os.environ["TAADAA_WORKER"] = "1"
    worker_sid = "env_worker_session"

    # 1. env_worker ghi ngoài whitelist -> BỊ CHẶN!
    res_wlist = check_worker_tool_gate("write_file", worker_sid, {"path": "C:/Windows/System32/drivers/etc/hosts"})
    assert res_wlist is not None
    assert "OUT OF WHITELIST" in res_wlist.get("reason", "")

    # 2. env_worker sửa guard plugin -> BỊ CHẶN!
    res_guard = check_worker_tool_gate("write_file", worker_sid, {"path": "C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard/__init__.py"})
    assert res_guard is not None
    assert "SELF-MODIFICATION BLOCKED" in res_guard.get("reason", "")


def test_adversarial_read_only_worker_cannot_write():
    """Adversarial test: Worker từ task non_code cố ghi file qua patch -> BỊ CHẶN READ-ONLY."""
    parent_sid = "parent_adv"
    worker_sid = "worker_adv"
    _PARENT_SESSION_CACHE[worker_sid] = parent_sid
    _update_session_state(parent_sid, {"target_files": []})

    res = check_worker_tool_gate("patch", worker_sid, {"path": "D:/Taadaa/automation-core/src/automation_core/startup.py"})
    assert res is not None
    assert res.get("action") == "block"
    assert "READ-ONLY WORKER" in res.get("reason", "")
