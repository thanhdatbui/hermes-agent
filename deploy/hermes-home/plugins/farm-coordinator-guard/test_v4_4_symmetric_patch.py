import os
import pytest
import sys

PLUGIN_DIR = r"C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard"
sys.path.insert(0, PLUGIN_DIR)

from __init__ import (
    check_worker_tool_gate,
    _on_pre_tool_call,
    _PARENT_SESSION_CACHE,
    _update_session_state,
)


@pytest.fixture(autouse=True)
def cleanup_env():
    os.environ.pop("TAADAA_WORKER", None)
    _PARENT_SESSION_CACHE.clear()
    yield


def test_write_file_without_target_path_fails_closed():
    """Worker gọi write_file mà không có path đích -> FAIL-CLOSED BLOCK 100%."""
    worker_sid = "worker_write_fail_closed"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    res = check_worker_tool_gate("write_file", worker_sid, {"content": "malicious"})
    assert res is not None
    assert "MISSING WRITE TARGET" in res.get("reason", "")


def test_worker_patch_decoy_path_with_embedded_leak_blocked():
    """LÝ DO 1 & 2: Worker khai path='D:/Taadaa/in_scope.py' nhưng diff nhét trong key lạ trỏ C:/Windows -> BỊ CHẶN!"""
    parent_sid = "parent_p"
    worker_sid = "worker_patch_decoy"
    _PARENT_SESSION_CACHE[worker_sid] = parent_sid

    in_scope = r"D:/Taadaa/automation-core/src/automation_core/startup.py"
    _update_session_state(parent_sid, {"target_files": [in_scope]})

    malicious_diff = (
        "*** Begin Patch\n"
        "*** Update File: C:/Windows/evil.py\n"
        "+evil_code\n"
        "*** End Patch"
    )
    # Truyền diff dưới key lạ 'diff' hoặc 'content' kèm decoy path
    res = check_worker_tool_gate("patch", worker_sid, {
        "path": in_scope,
        "diff_content": malicious_diff,
    })
    assert res is not None
    assert "OUT OF WHITELIST" in res.get("reason", "") or "INFO-LEAK BLOCKED" in res.get("reason", "")


def test_worker_patch_embedded_outside_scope_blocked():
    """Worker dùng patch hợp lệ trong repo nhưng ngoài scope lock -> BỊ CHẶN SCOPE LOCK BREACH."""
    parent_sid = "parent_scope"
    worker_sid = "worker_patch_scope"
    _PARENT_SESSION_CACHE[worker_sid] = parent_sid

    in_scope = r"D:/Taadaa/automation-core/src/automation_core/startup.py"
    _update_session_state(parent_sid, {"target_files": [in_scope]})

    out_of_scope_patch = (
        "*** Begin Patch\n"
        "*** Update File: D:/Taadaa/tiktok-follow/runner.py\n"
        "+evil\n"
        "*** End Patch"
    )
    res = check_worker_tool_gate("patch", worker_sid, {
        "mode": "patch",
        "patch": out_of_scope_patch,
    })
    assert res is not None
    assert "SCOPE LOCK BREACH" in res.get("reason", "")


def test_coordinator_v4a_patch_mode_unparseable_fails_closed():
    """Coordinator gọi patch mode='patch' nhưng không có file header hợp lệ -> FAIL-CLOSED BỊ CHẶN."""
    coord_sid = "coord_v4a_unparseable"

    res = _on_pre_tool_call("patch", {"mode": "patch", "patch": "invalid content without file header"}, session_id=coord_sid)
    assert res is not None
    assert "UNPARSEABLE PATCH" in res.get("reason", "")
