import os
import re
import pytest

import sys
PLUGIN_DIR = r"C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard"
sys.path.insert(0, PLUGIN_DIR)

from __init__ import _on_pre_tool_call, _update_session_state


@pytest.fixture(autouse=True)
def setup_session():
    # Đảm bảo không bị coi là worker session
    os.environ.pop("TAADAA_WORKER", None)
    sess_id = "test_guard_session_v2"
    _update_session_state(sess_id, {"phase": "ALERT", "inspect_budget": 1, "dispatch_count": 0})
    yield sess_id


def test_hole_1a_strange_real_path_in_free_text_ignored(setup_session):
    """Lỗ hổng 1a: Path lạ xuất hiện vu vơ trong free text (C:/Windows/...) không được coi là target file -> BỊ CHẶN MISSING TARGET FILE."""
    sess_id = setup_session
    res = _on_pre_tool_call(
        tool_name="delegate_task",
        args={
            "goal": "fix bug và sửa lỗi popup, screencap inspect_machine đã có",
            "context": "Xem file cấu hình tại C:/Windows/System32/drivers/etc/hosts rồi tự tìm hàm sửa",
        },
        session_id=sess_id,
    )
    assert res is not None
    assert res.get("action") == "block"
    assert "SCOPE LOCK MISSING TARGET FILE" in res.get("reason", "")


def test_hole_1b_strange_real_path_as_target_blocked(setup_session):
    """Lỗ hổng 1b: Cố tình đặt TARGET_FILE vào C:/Windows/... -> BỊ CHẶN BỞI WHITELIST HOẶC INVALID FILE TYPE."""
    sess_id = setup_session
    res = _on_pre_tool_call(
        tool_name="delegate_task",
        args={
            "goal": "fix bug và sửa lỗi popup, screencap inspect_machine đã có",
            "context": "TARGET_FILE: C:/Windows/System32/drivers/etc/hosts",
        },
        session_id=sess_id,
    )
    assert res is not None
    assert res.get("action") == "block"
    assert "OUT OF REPO WHITELIST" in res.get("reason", "") or "INVALID FILE TYPE" in res.get("reason", "")


def test_hole_2_directory_path_blocked(setup_session):
    """Lỗ hổng 2: Coordinator chỉ trỏ vào cả thư mục D:/Taadaa -> PHẢI BỊ CHẶN DIRECTORY NOT ALLOWED."""
    sess_id = setup_session
    res = _on_pre_tool_call(
        tool_name="delegate_task",
        args={
            "goal": "sửa code trong repo, screencap inspect_machine đã có",
            "context": "TARGET_FILE: D:/Taadaa",
        },
        session_id=sess_id,
    )
    assert res is not None
    assert res.get("action") == "block"
    assert "DIRECTORY NOT ALLOWED" in res.get("reason", "")


def test_hole_3_broad_trigger_catches_alternate_keywords(setup_session):
    """Lỗ hổng 3: Dùng từ ngữ khác (lỗi, khắc phục, timeout...) mà không có target file -> PHẢI BỊ CHẶN MISSING TARGET FILE."""
    sess_id = setup_session
    res = _on_pre_tool_call(
        tool_name="delegate_task",
        args={
            "goal": "khắc phục tình trạng timeout màn hình",
            "context": "vào flow tìm cách tối ưu lại",
        },
        session_id=sess_id,
    )
    assert res is not None
    assert res.get("action") == "block"
    assert "SCOPE LOCK MISSING TARGET FILE" in res.get("reason", "")


def test_hole_4_path_with_spaces_supported(setup_session):
    """Lỗ hổng 4: Path có khoảng trắng (tiktok-luot nuoi acc) -> ĐƯỢC NHẬN DIỆN VÀ CHO QUA."""
    sess_id = setup_session
    real_path_with_space = r"D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py"
    if os.path.isfile(real_path_with_space):
        res = _on_pre_tool_call(
            tool_name="delegate_task",
            args={
                "goal": "fix bug và sửa code",
                "context": f'screencap inspect_machine đã có. TARGET_FILE: "{real_path_with_space}"',
            },
            session_id=sess_id,
        )
        assert res is None  # Cho qua!


def test_valid_structured_target_files_allowed(setup_session):
    """Trường hợp chuẩn: Cung cấp file code thật qua target_files và có ground truth -> CHO QUA."""
    sess_id = setup_session
    real_file = r"D:/Taadaa/automation-core/src/automation_core/startup.py"
    if os.path.isfile(real_file):
        res = _on_pre_tool_call(
            tool_name="delegate_task",
            args={
                "goal": "fix bug và sửa code",
                "context": "screencap inspect_machine đã có.",
                "target_files": [real_file],
            },
            session_id=sess_id,
        )
        assert res is None  # Cho qua!
