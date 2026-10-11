import os
import pytest
import sys

PLUGIN_DIR = r"C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard"
sys.path.insert(0, PLUGIN_DIR)

from __init__ import (
    check_worker_tool_gate,
    _PARENT_SESSION_CACHE,
)


@pytest.fixture(autouse=True)
def cleanup_env():
    os.environ.pop("TAADAA_WORKER", None)
    _PARENT_SESSION_CACHE.clear()
    yield


def test_lo_1_search_files_without_path_is_fail_closed_blocked():
    """LỖ 1 CLOSED: search_files không có tham số path (chỉ có pattern) -> BỊ CHẶN 100%."""
    worker_sid = "worker_no_path"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    res = check_worker_tool_gate("search_files", worker_sid, {"pattern": "AWS_SECRET"})
    assert res is not None
    assert "OUT OF WHITELIST" in res.get("reason", "") or "MISSING EXPLICIT PATH" in res.get("reason", "")


def test_lo_2_bare_filename_resolves_and_enforces_whitelist():
    """LỖ 2 CLOSED: read_file với tên trần (bare filename) được resolve qua realpath và bắt buộc nằm trong D:/Taadaa."""
    worker_sid = "worker_bare_file"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    # Tên trần 'phase.json' trong CWD hiện tại (C:/Users/Kibe) -> BỊ CHẶN OUT OF WHITELIST!
    res = check_worker_tool_gate("read_file", worker_sid, {"path": "phase.json"})
    assert res is not None
    assert "OUT OF WHITELIST" in res.get("reason", "")


def test_lo_3_git_diff_extra_path_enforces_whitelist():
    """LỖ 3 CLOSED: git diff với path ngoài repo sau dấu '--' -> BỊ CHẶN OUT OF WHITELIST."""
    worker_sid = "worker_git_path"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    cmd = r"git diff -- C:\Users\Kibe\some_file.py"
    res = check_worker_tool_gate("terminal", worker_sid, {"command": cmd})
    assert res is not None
    assert "OUT OF WHITELIST" in res.get("reason", "")
