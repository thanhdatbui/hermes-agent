import os
import pytest
import sys

PLUGIN_DIR = r"C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard"
sys.path.insert(0, PLUGIN_DIR)

from __init__ import _on_pre_tool_call, check_worker_tool_gate, _update_session_state


@pytest.fixture(autouse=True)
def cleanup_env():
    os.environ.pop("TAADAA_WORKER", None)
    yield


def test_hole_a_worker_scope_lock_enforcement():
    """HOLE A: Worker bị cấm sửa file ngoài danh sách target_files của Coordinator cha."""
    parent_sid = "coord_session_123"
    worker_sid = "worker_session_456"

    # Coordinator khai báo target_files = ['D:/Taadaa/automation-core/src/automation_core/startup.py']
    target_file = r"D:/Taadaa/automation-core/src/automation_core/startup.py"
    _update_session_state(parent_sid, {
        "phase": "WORKER_RUNNING",
        "target_files": [target_file],
    })

    # Giả lập worker có parent_session_id trỏ về parent_sid
    from __init__ import _PARENT_SESSION_CACHE
    _PARENT_SESSION_CACHE[worker_sid] = parent_sid

    # 1. Worker sửa đúng file được giao -> CHO PHÉP
    res_ok = check_worker_tool_gate("patch", worker_sid, {"path": target_file})
    assert res_ok is None

    # 2. Worker sửa file test cùng thư mục -> CHO PHÉP
    test_file = r"D:/Taadaa/automation-core/src/automation_core/test_startup.py"
    res_test = check_worker_tool_gate("write_file", worker_sid, {"path": test_file})
    assert res_test is None

    # 3. Worker cố tình sửa file lạ ngoài repo khác -> BỊ CHẶN!
    breach_file = r"D:/Taadaa/tiktok-follow/runner.py"
    res_breach = check_worker_tool_gate("patch", worker_sid, {"path": breach_file})
    assert res_breach is not None
    assert res_breach.get("action") == "block"
    assert "SCOPE LOCK BREACH" in res_breach.get("reason", "")


def test_hole_b_prose_accidental_path_not_treated_as_target():
    """HOLE B: Path xuất hiện tình cờ trong văn xuôi không có header -> BỊ CHẶN MISSING TARGET FILE."""
    sess_id = "coord_session_b"
    _update_session_state(sess_id, {"phase": "ALERT", "inspect_budget": 1, "dispatch_count": 0})

    # Văn xuôi có nhắc đến một file có thật trong D:/Taadaa nhưng không có TARGET_FILE:
    res = _on_pre_tool_call(
        tool_name="delegate_task",
        args={
            "goal": "fix bug và cải thiện logic",
            "context": "screencap đã có. Xem ví dụ tương tự ở D:/Taadaa/automation-core/src/automation_core/startup.py rồi tự làm",
        },
        session_id=sess_id,
    )
    assert res is not None
    assert res.get("action") == "block"
    assert "SCOPE LOCK MISSING TARGET FILE" in res.get("reason", "")


def test_hole_c_default_deny_catches_creative_wording_in_idle():
    """HOLE C: Dùng từ ngữ lạ ở phase IDLE mà không khai báo target_files -> DEFAULT-DENY BỊ CHẶN."""
    sess_id = "coord_session_c"
    _update_session_state(sess_id, {"phase": "IDLE", "dispatch_count": 0})

    res = _on_pre_tool_call(
        tool_name="delegate_task",
        args={
            "goal": "tinh chỉnh và làm mượt mà luồng xử lý",
            "context": "vào hệ thống dọn dẹp các điểm nghẽn",
        },
        session_id=sess_id,
    )
    assert res is not None
    assert res.get("action") == "block"
    assert "SCOPE LOCK MISSING TARGET FILE" in res.get("reason", "")


def test_hole_d_create_new_file_with_valid_parent():
    """HOLE D: Tạo file mới chưa tồn tại nhưng thư mục cha hợp lệ -> CHO PHÉP."""
    sess_id = "coord_session_d"
    _update_session_state(sess_id, {"phase": "IDLE", "dispatch_count": 0})

    new_file = r"D:/Taadaa/automation-core/src/automation_core/new_feature_sample.py"
    if os.path.exists(new_file):
        os.remove(new_file)

    res = _on_pre_tool_call(
        tool_name="delegate_task",
        args={
            "goal": "tạo module mới",
            "target_files": [new_file],
        },
        session_id=sess_id,
    )
    assert res is None  # Cho phép vì parent dir D:/Taadaa/automation-core/src/automation_core tồn tại!


def test_guard_self_modification_blacklisted():
    """Cố tình Scope Lock hoặc Worker sửa file của chính guard -> BỊ CHẶN."""
    sess_id = "coord_session_self"
    _update_session_state(sess_id, {"phase": "IDLE", "dispatch_count": 0})

    guard_file = r"C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard/__init__.py"
    res = _on_pre_tool_call(
        tool_name="delegate_task",
        args={
            "goal": "sửa bug guard",
            "target_files": [guard_file],
        },
        session_id=sess_id,
    )
    assert res is not None
    assert res.get("action") == "block"
    assert "GUARD SOURCE BLACKLISTED" in res.get("reason", "")
