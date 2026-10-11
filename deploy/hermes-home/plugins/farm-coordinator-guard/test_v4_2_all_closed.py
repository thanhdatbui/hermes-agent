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


def test_write_file_without_target_path_fails_closed():
    """LÝ DO 1: Worker gọi write_file mà không có path đích -> FAIL-CLOSED BLOCK 100%."""
    worker_sid = "worker_write_fail_closed"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    res = check_worker_tool_gate("write_file", worker_sid, {"content": "malicious"})
    assert res is not None
    assert "MISSING WRITE TARGET" in res.get("reason", "")


def test_git_diff_bare_filename_after_dash_enforces_whitelist():
    """LÝ DO 2: Token tên trần sau '--' trong git diff được resolve qua realpath và bắt buộc nằm trong D:/Taadaa."""
    worker_sid = "worker_git_bare_file"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    cmd = "git diff -- secret.txt"
    res = check_worker_tool_gate("terminal", worker_sid, {"command": cmd})
    assert res is not None
    assert "OUT OF WHITELIST" in res.get("reason", "")


def test_coordinator_v4a_patch_add_file_outside_whitelist_blocked():
    """V4A PATCH CAVEAT: Coordinator dùng patch *** Add File: C:/Startup/payload.py -> BỊ CHẶN PATCH OUT OF WHITELIST."""
    coord_sid = "coord_v4a_test"

    malicious_patch = (
        "*** Begin Patch\n"
        "*** Add File: C:/Users/Kibe/AppData/Roaming/Startup/payload.py\n"
        "+evil_code\n"
        "*** End Patch"
    )
    res = _on_pre_tool_call("patch", {"patch": malicious_patch}, session_id=coord_sid)
    assert res is not None
    assert "PATCH OUT OF WHITELIST" in res.get("reason", "")


def test_coordinator_v4a_patch_unparseable_fails_closed():
    """V4A PATCH CAVEAT: Patch không có bất kỳ file header hợp lệ nào -> FAIL-CLOSED BỊ CHẶN."""
    coord_sid = "coord_v4a_unparseable"

    unparseable_patch = "random text without file headers"
    res = _on_pre_tool_call("patch", {"patch": unparseable_patch}, session_id=coord_sid)
    assert res is not None
    assert "UNPARSEABLE PATCH" in res.get("reason", "")
