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


def test_chaining_and_metacharacters_hard_blocked():
    """CHÍ MẠNG 1: Toàn bộ shell chaining (; && || | $ ` > < () \\) bị chặn đứng 100%."""
    worker_sid = "worker_chaining"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    # 1. pytest ; python -c "..." -> BỊ CHẶN!
    res1 = check_worker_tool_gate("terminal", worker_sid, {"command": "pytest ; python -c 'import os'"})
    assert res1 is not None
    assert "HERMETIC SHELL" in res1.get("reason", "")

    # 2. git diff && python evil.py -> BỊ CHẶN!
    res2 = check_worker_tool_gate("terminal", worker_sid, {"command": "git diff && python evil.py"})
    assert res2 is not None
    assert "HERMETIC SHELL" in res2.get("reason", "")

    # 3. git status | python -> BỊ CHẶN!
    res3 = check_worker_tool_gate("terminal", worker_sid, {"command": "git status | python -c '...' "})
    assert res3 is not None
    assert "HERMETIC SHELL" in res3.get("reason", "")

    # 4. python -c "..." ; echo inspect_machine.py -> BỊ CHẶN!
    res4 = check_worker_tool_gate("terminal", worker_sid, {"command": 'python -c "rm -rf" ; echo inspect_machine.py'})
    assert res4 is not None
    assert "HERMETIC SHELL" in res4.get("reason", "")


def test_unconditional_state_db_and_guard_protection():
    """CHÍ MẠNG 2: Bất kỳ lệnh terminal nào đụng đến state.db hoặc guard đều bị chặn vô điều kiện."""
    # Coordinator hay Worker cũng đều bị chặn nếu đụng vào state.db hoặc guard source
    coord_sid = "coord_unconditional"
    _update_session_state(coord_sid, {"is_coordinator": True, "phase": "IDLE"})

    # 1. Lệnh terminal đọc hoặc ghi state.db -> BỊ CHẶN VÔ ĐIỀU KIỆN!
    res1 = _on_pre_tool_call("terminal", {"command": "cat C:/Users/Kibe/AppData/Local/hermes/state.db"}, session_id=coord_sid)
    assert res1 is not None
    assert "GUARD SELF-PROTECTION" in res1.get("reason", "")

    # 2. Lệnh terminal đụng farm-coordinator-guard -> BỊ CHẶN VÔ ĐIỀU KIỆN!
    res2 = _on_pre_tool_call("terminal", {"command": "ls C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard"}, session_id=coord_sid)
    assert res2 is not None
    assert "GUARD SELF-PROTECTION" in res2.get("reason", "")


def test_lock_fails_closed_raises_error(monkeypatch):
    """CHÍ MẠNG 3: File lock khi nghẽn quá 3s sẽ RAISE RuntimeError (fail-closed, không bao giờ yield)."""
    from __init__ import _acquire_file_lock
    import pathlib

    test_lock = pathlib.Path(PLUGIN_DIR) / "test_simulated.lock"
    # Tạo lock file trước
    with open(test_lock, "w") as f:
        f.write("locked")

    # Giảm thời gian chờ xuống 0.1s để test nhanh
    try:
        with _acquire_file_lock(test_lock):
            assert False, "Không được phép yield khi đang kẹt lock!"
    except RuntimeError as exc:
        assert "LOCK FAIL-CLOSED" in str(exc)
    finally:
        if test_lock.exists():
            test_lock.unlink()


def test_legitimate_worker_test_commands_pass():
    """Các lệnh kiểm thử hợp lệ, không chứa ký tự nối lệnh -> CHO PHÉP."""
    worker_sid = "worker_valid"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    assert check_worker_tool_gate("terminal", worker_sid, {"command": "pytest -v tests/test_core.py"}) is None
    assert check_worker_tool_gate("terminal", worker_sid, {"command": "python -m pytest tests/"}) is None
    assert check_worker_tool_gate("terminal", worker_sid, {"command": "git diff"}) is None
    assert check_worker_tool_gate("terminal", worker_sid, {"command": "git -C D:/Taadaa diff"}) is None
    assert check_worker_tool_gate("terminal", worker_sid, {"command": "python D:/Taadaa/tools/inspect_machine.py 41"}) is None
