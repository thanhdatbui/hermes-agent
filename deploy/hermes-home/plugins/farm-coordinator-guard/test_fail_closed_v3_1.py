import os
import pytest
import sys

PLUGIN_DIR = r"C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard"
sys.path.insert(0, PLUGIN_DIR)

from __init__ import (
    _on_pre_tool_call,
    _is_worker_session,
    _is_known_coordinator_session,
    check_worker_tool_gate,
    _update_session_state,
    _PARENT_SESSION_CACHE,
)


@pytest.fixture(autouse=True)
def cleanup_env():
    os.environ.pop("TAADAA_WORKER", None)
    os.environ.pop("TAADAA_SCOPE_FILES", None)
    _PARENT_SESSION_CACHE.clear()
    yield


def test_critical_fail_closed_unknown_session_treated_as_worker():
    """CRITICAL: Một session hoàn toàn lạ (chưa kịp vào DB, race condition) đi qua _on_pre_tool_call
    BẮT BUỘC bị xử lý như UNTRUSTED WORKER -> CẤM execute_code, CẤM terminal cp, CẤM write_file ngoài scope!
    """
    untrusted_sid = "totally_unknown_race_condition_session_999"

    # 1. execute_code -> BỊ ACTION LOCK CHẶN 100%
    res_code = _on_pre_tool_call("execute_code", {"code": "print('hello')"}, session_id=untrusted_sid)
    assert res_code is not None
    assert res_code.get("action") == "block"
    assert "ACTION LOCK" in res_code.get("reason", "")

    # 2. terminal cp/copy -> BỊ ACTION LOCK CHẶN 100%
    res_term = _on_pre_tool_call("terminal", {"command": "cp evil.py D:/Taadaa/startup.py"}, session_id=untrusted_sid)
    assert res_term is not None
    assert res_term.get("action") == "block"
    assert "ACTION LOCK" in res_term.get("reason", "")

    # 3. write_file bừa bãi khi không có scope lock -> BỊ CHẶN READ-ONLY 100%
    res_write = _on_pre_tool_call("write_file", {"path": "D:/Taadaa/automation-core/README.md", "content": "bad"}, session_id=untrusted_sid)
    assert res_write is not None
    assert res_write.get("action") == "block"
    assert "READ-ONLY WORKER" in res_write.get("reason", "")


def test_critical_no_none_caching_and_no_sticky_privilege():
    """CRITICAL: Gọi _get_parent_session_id trên session lạ KHÔNG được cache None vào _PARENT_SESSION_CACHE."""
    from __init__ import _get_parent_session_id
    unknown_sid = "unknown_session_not_in_db"
    res = _get_parent_session_id(unknown_sid)
    assert res is None
    # Xác nhận _PARENT_SESSION_CACHE không chứa unknown_sid
    assert unknown_sid not in _PARENT_SESSION_CACHE


def test_env_worker_with_scope_files_can_write_target():
    """M-6: env_worker với TAADAA_SCOPE_FILES được cấp phép sửa đúng target file."""
    os.environ["TAADAA_WORKER"] = "1"
    target = r"D:/Taadaa/automation-core/src/automation_core/startup.py"
    os.environ["TAADAA_SCOPE_FILES"] = target
    worker_sid = "env_worker_with_scope"

    # Sửa đúng target -> Cho phép
    res = check_worker_tool_gate("patch", worker_sid, {"path": target})
    assert res is None

    # Sửa ngoài target -> Bị chặn!
    res_outside = check_worker_tool_gate("patch", worker_sid, {"path": "D:/Taadaa/tiktok-follow/runner.py"})
    assert res_outside is not None
    assert "SCOPE LOCK BREACH" in res_outside.get("reason", "")


def test_known_coordinator_positive_proof_allowed_delegate():
    """Session đã xác thực dương tính là Coordinator được phép điều phối delegate_task."""
    coord_sid = "positive_verified_coordinator"
    _update_session_state(coord_sid, {"is_coordinator": True, "phase": "IDLE"})

    assert _is_known_coordinator_session(coord_sid) is True
    assert _is_worker_session(coord_sid) is False
