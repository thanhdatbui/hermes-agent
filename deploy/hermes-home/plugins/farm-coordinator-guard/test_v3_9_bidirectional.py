import os
import pytest
import sys

PLUGIN_DIR = r"C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard"
sys.path.insert(0, PLUGIN_DIR)

from __init__ import (
    check_worker_tool_gate,
    _on_pre_tool_call,
    _PARENT_SESSION_CACHE,
)


@pytest.fixture(autouse=True)
def cleanup_env():
    os.environ.pop("TAADAA_WORKER", None)
    _PARENT_SESSION_CACHE.clear()
    yield


def test_ancestor_leak_blocked_bidirectional():
    """Worker dùng search_files trỏ vào thư mục cha C:/Users/Kibe hoặc HERMES_ROOT để leak ~/.ssh -> BỊ CHẶN."""
    worker_sid = "worker_leak_ancestor"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    # 1. search_files trỏ C:/Users/Kibe -> BỊ CHẶN!
    res1 = check_worker_tool_gate("search_files", worker_sid, {"path": r"C:/Users/Kibe"})
    assert res1 is not None
    assert "OUT OF WHITELIST" in res1.get("reason", "") or "INFO-LEAK BLOCKED" in res1.get("reason", "")

    # 2. search_files trỏ C:/Users/Kibe/AppData/Local/hermes -> BỊ CHẶN!
    res2 = check_worker_tool_gate("search_files", worker_sid, {"path": r"C:/Users/Kibe/AppData/Local/hermes"})
    assert res2 is not None
    assert "INFO-LEAK BLOCKED" in res2.get("reason", "")


def test_read_file_unconditional_shield_actually_blocks():
    """Unconditional shield thực sự return block khi read_file đọc file được bảo vệ."""
    coord_sid = "coord_read_shield"

    res = _on_pre_tool_call("read_file", {"path": r"C:/Users/Kibe/AppData/Local/hermes/state.db"}, session_id=coord_sid)
    assert res is not None
    assert res.get("action") == "block"
    assert "GUARD SELF-PROTECTION" in res.get("reason", "")
