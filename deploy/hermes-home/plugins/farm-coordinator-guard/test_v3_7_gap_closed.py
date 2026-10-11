import os
import pytest
import sys

PLUGIN_DIR = r"C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard"
sys.path.insert(0, PLUGIN_DIR)

from __init__ import (
    _on_pre_tool_call,
    check_worker_tool_gate,
    _PARENT_SESSION_CACHE,
)


@pytest.fixture(autouse=True)
def cleanup_env():
    os.environ.pop("TAADAA_WORKER", None)
    _PARENT_SESSION_CACHE.clear()
    yield


def test_gap_1_worker_tool_level_default_deny():
    """GAP 1: Worker gọi bất kỳ tool nào ngoài WORKER_ALLOWED_TOOLS -> BỊ CHẶN 100%."""
    worker_sid = "worker_tool_deny"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    # 1. execute_code -> BỊ CHẶN!
    res_code = check_worker_tool_gate("execute_code", worker_sid, {"code": "print(1)"})
    assert res_code is not None
    assert "TOOL DEFAULT-DENY" in res_code.get("reason", "")

    # 2. browser_navigate -> BỊ CHẶN!
    res_browser = check_worker_tool_gate("browser_navigate", worker_sid, {"url": "http://evil.com"})
    assert res_browser is not None
    assert "TOOL DEFAULT-DENY" in res_browser.get("reason", "")

    # 3. delegate_task -> BỊ CHẶN!
    res_delegate = check_worker_tool_gate("delegate_task", worker_sid, {"goal": "spawn subworker"})
    assert res_delegate is not None
    assert "TOOL DEFAULT-DENY" in res_delegate.get("reason", "")

    # 4. shell / bash -> BỊ CHẶN!
    res_shell = check_worker_tool_gate("shell", worker_sid, {"cmd": "ls"})
    assert res_shell is not None
    assert "TOOL DEFAULT-DENY" in res_shell.get("reason", "")


def test_gap_2_git_hermetic_env_enforced():
    """GAP 2: Lệnh git của worker tự động kích hoạt hermetic environment."""
    worker_sid = "worker_git_env"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    res = check_worker_tool_gate("terminal", worker_sid, {"command": "git diff"})
    assert res is None
    # Xác nhận các biến môi trường git an toàn đã được ép lập
    assert os.environ.get("GIT_PAGER") == "cat"
    assert os.environ.get("GIT_EXTERNAL_DIFF") == ""
    assert os.environ.get("GIT_CONFIG_NOSYSTEM") == "1"
