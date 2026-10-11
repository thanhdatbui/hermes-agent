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
    _validate_worker_terminal_command,
)


@pytest.fixture(autouse=True)
def cleanup_env():
    os.environ.pop("TAADAA_WORKER", None)
    _PARENT_SESSION_CACHE.clear()
    yield


def test_malicious_pytest_with_state_db_access_blocked():
    """Worker chạy pytest nhưng file test chứa mã độc truy cập state.db -> BỊ CHẶN."""
    worker_sid = "worker_malicious_test"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    malicious_test = r"C:/Users/Kibe/AppData/Local/hermes/tmp/test_evil.py"
    os.makedirs(os.path.dirname(malicious_test), exist_ok=True)
    with open(malicious_test, "w", encoding="utf-8") as f:
        f.write("import sqlite3\ncon = sqlite3.connect('state.db')\n")

    try:
        res = check_worker_tool_gate("terminal", worker_sid, {"command": f"pytest {malicious_test}"})
        assert res is not None
        assert "MALICIOUS TEST BLOCKED" in res.get("reason", "")
    finally:
        if os.path.exists(malicious_test):
            os.remove(malicious_test)


def test_exact_inspect_machine_path_matching():
    """Lệnh inspect_machine chỉ cho phép đường dẫn chuẩn D:/Taadaa/tools/inspect_machine.py <N>."""
    worker_sid = "worker_inspect"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    # Đường dẫn chuẩn -> Cho phép
    assert check_worker_tool_gate("terminal", worker_sid, {"command": "python D:/Taadaa/tools/inspect_machine.py 41"}) is None

    # Tên giả mạo ở thư mục khác (fake_inspect_machine.py) -> Bị chặn!
    res_fake = check_worker_tool_gate("terminal", worker_sid, {"command": "python D:/Taadaa/fake_inspect_machine.py 41"})
    assert res_fake is not None
    assert "DEFAULT-DENY TERMINAL" in res_fake.get("reason", "")


def test_windows_path_with_backslashes_allowed():
    """Đường dẫn Windows chứa dấu backslash không bị coi là shell metacharacter."""
    worker_sid = "worker_winpath"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    cmd = r"pytest -v tests\test_unit.py"
    # Không bị chặn bởi HERMETIC SHELL
    err = _validate_worker_terminal_command(cmd)
    assert err is None
