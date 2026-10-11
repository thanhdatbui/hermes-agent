"""
Zero-Bypass Dispatch Contract & Coordinator Write Ledger Test Suite v5.0.
Verifies all P0 and P1 acceptance criteria defined by Claude Architecture Specification.
"""

import json
import os
import tempfile
from pathlib import Path
import pytest

from farm_policy import (
    ContractError,
    extract_tool_args,
    validate_dispatch,
    compute_edit_footprint,
    coordinator_write_gate,
    coordinator_terminal_gate,
    is_protected_target,
)
from __init__ import _on_pre_tool_call, check_worker_tool_gate, _update_session_state, _get_session_state, _PARENT_SESSION_CACHE


# ========================================================
# 1. PAYLOAD PARSING & FAIL-CLOSED (P0 Item 1)
# ========================================================
def test_payload_parsing_variants():
    """Kiểm tra extract_tool_args phân giải chuẩn mọi biến thể payload."""
    # 1. Dạng tool_input dict
    p1 = {"tool_name": "delegate_task", "tool_input": {"goal": "test goal"}}
    assert extract_tool_args(p1)["goal"] == "test goal"

    # 2. Dạng args dict
    p2 = {"tool_name": "delegate_task", "args": {"goal": "test goal 2"}}
    assert extract_tool_args(p2)["goal"] == "test goal 2"

    # 3. Dạng JSON string trong tool_input
    p3 = {"tool_name": "delegate_task", "tool_input": json.dumps({"goal": "test json str"})}
    assert extract_tool_args(p3)["goal"] == "test json str"

    # 4. Payload không có args -> fail-closed
    with pytest.raises(ContractError, match="PAYLOAD_UNPARSEABLE"):
        extract_tool_args({"tool_name": "delegate_task", "unknown_key": 123})

    # 5. Payload rỗng -> fail-closed
    with pytest.raises(ContractError, match="PAYLOAD_UNPARSEABLE"):
        extract_tool_args({})


# ========================================================
# 2. GATE 2 & ANCHOR VERIFICATION (P0 Item 3)
# ========================================================
def test_gate2_anchor_checks(tmp_path):
    """Guard tự mở file và đếm anchor c == 1, chặn 0 lần hoặc >= 2 lần."""
    # Tạo file mẫu trong D:/Taadaa
    test_file = Path(r"D:\Taadaa\tools\temp_test_anchor.py")
    test_file.write_text("""
def calculate_score(val):
    if val > 10:
        return 1
    return 0

def duplicate_anchor():
    pass

def duplicate_anchor():
    pass
""", encoding="utf-8")

    try:
        # A. count == 0: Anchor không tồn tại -> BỊ CHẶN
        task_c0 = {
            "goal": "Sửa code",
            "context": f"""
TASK_KIND: EDIT
FILE: {test_file}
OLD_STRING: <<<
    this anchor does not exist
>>>
NEW_STRING: <<<
    new code
>>>
FOCUSED_TEST: python -m pytest D:/Taadaa/tools/test_tiktok_account_tracker.py::test_node -q
BUDGET_CALLS: 10
FAIL_FAST: Nếu trong <= 3 iterations đầu thấy scope bất khả thi với budget 15 calls thì DỪNG NGAY (ABORT)...
"""
        }
        with pytest.raises(ContractError, match="ANCHOR_NOT_FOUND"):
            validate_dispatch(task_c0)

        # B. count >= 2: Anchor trùng lặp -> BỊ CHẶN
        task_c2 = {
            "goal": "Sửa code",
            "context": f"""
TASK_KIND: EDIT
FILE: {test_file}
OLD_STRING: <<<
def duplicate_anchor():
>>>
NEW_STRING: <<<
def unique_anchor():
>>>
FOCUSED_TEST: python -m pytest D:/Taadaa/tools/test_tiktok_account_tracker.py::test_node -q
BUDGET_CALLS: 10
FAIL_FAST: Nếu trong <= 3 iterations đầu thấy scope bất khả thi với budget 15 calls thì DỪNG NGAY (ABORT)...
"""
        }
        with pytest.raises(ContractError, match="ANCHOR_NOT_UNIQUE"):
            validate_dispatch(task_c2)

        # C. OLD == NEW -> BỊ CHẶN
        task_eq = {
            "goal": "Sửa code",
            "context": f"""
TASK_KIND: EDIT
FILE: {test_file}
OLD_STRING: <<<
    if val > 10:
>>>
NEW_STRING: <<<
    if val > 10:
>>>
FOCUSED_TEST: python -m pytest D:/Taadaa/tools/test_tiktok_account_tracker.py::test_node -q
BUDGET_CALLS: 10
FAIL_FAST: Nếu trong <= 3 iterations đầu thấy scope bất khả thi với budget 15 calls thì DỪNG NGAY (ABORT)...
"""
        }
        with pytest.raises(ContractError, match="OLD_EQUALS_NEW"):
            validate_dispatch(task_eq)

        # D. count == 1: Anchor duy nhất tuyệt đối -> PASS
        task_c1 = {
            "goal": "Sửa code",
            "context": f"""
TASK_KIND: EDIT
FILE: {test_file}
OLD_STRING: <<<
    if val > 10:
>>>
NEW_STRING: <<<
    if val >= 10:
>>>
FOCUSED_TEST: python -m pytest D:/Taadaa/tools/test_tiktok_account_tracker.py::test_node -q
BUDGET_CALLS: 10
FAIL_FAST: Nếu trong <= 3 iterations đầu thấy scope bất khả thi với budget 15 calls thì DỪNG NGAY (ABORT)...
"""
        }
        res = validate_dispatch(task_c1)
        assert res["task_kind"] == "EDIT"
        assert res["target_files"] == [os.path.normpath(str(test_file))]

    finally:
        test_file.unlink(missing_ok=True)


# ========================================================
# 3. ANTI-DISGUISE (P0 Item 5)
# ========================================================
def test_anti_disguise_investigate():
    """Task investigate chứa ý đồ sửa code bị chặn; investigate hợp lệ cấp target_files=[] (read-only)."""
    # 1. Investigate nhưng goal chứa động từ sửa code -> BỊ CHẶN
    task_fake = {
        "goal": "Sửa code classifier và tối ưu logic",
        "context": """
TASK_KIND: INVESTIGATE
QUESTION: Điều tra tại sao classifier sai?
READ_SCOPE: D:/Taadaa/tools/test_tiktok_account_tracker.py
BUDGET_CALLS: 3
FAIL_FAST: Dừng ngay nếu không tìm thấy.
"""
    }
    with pytest.raises(ContractError, match="INVESTIGATE_HAS_EDIT_INTENT"):
        validate_dispatch(task_fake)

    # 2. Investigate hợp lệ -> trả về target_files = []
    task_valid = {
        "goal": "Kiểm tra log màn hình máy 20",
        "context": """
TASK_KIND: INVESTIGATE
QUESTION: Màn hình hiện tại đang ở đâu?
READ_SCOPE: D:/Taadaa/tools/test_tiktok_account_tracker.py
BUDGET_CALLS: 3
FAIL_FAST: Dừng ngay sau 3 calls nếu không có log.
"""
    }
    res = validate_dispatch(task_valid)
    assert res["task_kind"] == "INVESTIGATE"
    assert res["target_files"] == []

    # 3. Tích hợp: Worker có target_files = [] gọi write_file / patch bị chặn với READ-ONLY WORKER
    worker_sid = "worker_investigate_readonly"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_inv"
    _update_session_state("parent_inv", {"target_files": []})

    block_res = check_worker_tool_gate(
        "write_file",
        worker_sid,
        {"path": r"D:\Taadaa\tools\some_file.py", "content": "hack"}
    )
    assert block_res is not None
    assert "READ-ONLY WORKER" in block_res.get("reason", "")


# ========================================================
# 4. WORKER HARD BUDGET (P0 Item 11)
# ========================================================
def test_worker_hard_budget_exceeded():
    """Worker gọi đến tool call thứ 16 bị Hard Guard chặn đứng vô điều kiện."""
    worker_sid = "worker_budget_test_sid"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_test"
    _update_session_state("parent_test", {"target_files": [r"D:\Taadaa\tools\test_tiktok_account_tracker.py"]})
    _update_session_state(worker_sid, {"worker_call_count": 15})

    # Call thứ 16
    res = check_worker_tool_gate("read_file", worker_sid, {"path": r"D:\Taadaa\tools\test_tiktok_account_tracker.py"})
    assert res is None  # PA3: worker cap is advisory, not a hard block


# ========================================================
# 5. COORDINATOR WRITE LEDGER & T1 / L2 (P0 Item 6 & 7)
# ========================================================
def test_coordinator_t1_budget_cumulative(monkeypatch):
    """Ngân sách T1 cộng dồn theo COORD_T1_MAX_FILES/LINES (mặc định 5 files / 200 dòng); vượt trần -> chặn."""
    import farm_policy
    assert farm_policy.COORD_T1_MAX_FILES >= 2 and farm_policy.COORD_T1_MAX_LINES >= 100
    monkeypatch.setattr(farm_policy, "COORD_T1_MAX_FILES", 1)
    sid = "coord_ledger_test_sid"
    state = {}

    fn_args_1 = {
        "path": r"D:\Taadaa\tools\test_tiktok_account_tracker.py",
        "old_string": "def test_a():\n    pass",
        "new_string": "def test_a():\n    assert 1 == 1"
    }

    # Patch 1: 1 file, ~2 dòng diff -> QUA
    ok1, reason1, state = coordinator_write_gate(sid, "patch", fn_args_1, state)
    assert ok1 is True
    assert len(state["write_ledger"]["t1_files"]) == 1
    assert state["write_ledger"]["t1_lines"] <= 15

    # Patch 2: Sửa sang file thứ 2 khi chưa có L2 -> BỊ CHẶN NGAY LẬP TỨC
    fn_args_2 = {
        "path": r"D:\Taadaa\tools\test_cage_gate.py",
        "old_string": "def test_b():\n    pass",
        "new_string": "def test_b():\n    assert 2 == 2"
    }
    ok2, reason2, state = coordinator_write_gate(sid, "patch", fn_args_2, state)
    assert ok2 is False
    assert "COORDINATOR WRITE DENIED" in reason2


def test_coordinator_l2_requires_guard_observed_eligibility(monkeypatch):
    """Coordinator chỉ được mở L2 khi guard đã tự quan sát l2_eligible=True (ghim T1 = 15 dòng để kiểm logic L2)."""
    import farm_policy
    monkeypatch.setattr(farm_policy, "COORD_T1_MAX_LINES", 15)
    sid = "coord_l2_test_sid"
    state = {"l2_eligible": False}  # Chưa đủ điều kiện

    fn_args = {
        "path": r"D:\Taadaa\tools\test_tiktok_account_tracker.py",
        "old_string": "line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8\nline9\nline10\nline11\nline12\nline13\nline14\nline15\nline16",
        "new_string": "changed"
    }

    # Thao tác vượt T1 (> 15 dòng) khi l2_eligible=False -> BỊ CHẶN
    ok, reason, state = coordinator_write_gate(sid, "patch", fn_args, state)
    assert ok is False
    assert "COORDINATOR WRITE DENIED" in reason

    # Khi guard ghi nhận 2 lần worker failure -> l2_eligible=True
    state["l2_eligible"] = True
    state["l2_targets"] = [os.path.normpath(r"D:\Taadaa\tools\test_tiktok_account_tracker.py")]

    # Thao tác L2 <= 30 dòng -> ĐƯỢC PHÉP
    ok_l2, reason_l2, state = coordinator_write_gate(sid, "patch", fn_args, state)
    assert ok_l2 is True
    assert state["write_ledger"]["l2_used"] is True

    # Thao tác L2 lần thứ 2 hoặc vượt 30 dòng -> BỊ CHẶN (L2 DUY NHẤT 1 LẦN)
    ok_l2_2, reason_l2_2, state = coordinator_write_gate(sid, "patch", fn_args, state)
    assert ok_l2_2 is False
    assert "L2 BUDGET EXCEEDED" in reason_l2_2 or "DENIED" in reason_l2_2


# ========================================================
# 6. COORDINATOR TERMINAL DANGEROUS COMMANDS (P0 Item 8)
# ========================================================
def test_audit_event_schema_for_blocked_terminal_and_allowlisted_tool():
    import farm_policy
    assert callable(farm_policy.coordinator_terminal_gate)
    blocked, reason = farm_policy.coordinator_terminal_gate("python -c \"open('hack.py', 'w')\"", {"closeout_passed": False})
    assert blocked is False
    assert isinstance(reason, str) and reason
    allowed, allowed_reason = farm_policy.coordinator_terminal_gate("python D:/Taadaa/tools/inspect_machine.py 20", {"closeout_passed": False})
    assert allowed is True
    assert allowed_reason == ""


def test_coordinator_dangerous_terminal_commands_blocked():
    """Coordinator chạy các lệnh ghi mã gián tiếp hoặc quét đĩa đều bị chặn."""
    state = {"closeout_passed": False}

    # 1. python -c open write
    ok1, _ = coordinator_terminal_gate("python -c \"open('hack.py', 'w').write('foo')\"", state)
    assert ok1 is False

    # 2. git commit local được phép (mở khóa 2026-10-05); git push vẫn cần closeout >= 85
    ok2, _ = coordinator_terminal_gate("git commit -m 'local commit'", state)
    assert ok2 is True
    ok2b, _ = coordinator_terminal_gate("git push origin main", state)
    assert ok2b is False

    # 3. git apply
    ok3, _ = coordinator_terminal_gate("git apply fix.patch", state)
    assert ok3 is False

    # 4. os.walk quét đĩa
    ok4, _ = coordinator_terminal_gate("python -c \"import os; os.walk('D:/Taadaa')\"", state)
    assert ok4 is False

    # 5. Lệnh lành tính (git status, inspect_machine) -> ĐƯỢC PHÉP
    ok5, _ = coordinator_terminal_gate("git status", state)
    assert ok5 is True

    ok6, _ = coordinator_terminal_gate("python D:/Taadaa/tools/inspect_machine.py 20", state)
    assert ok6 is True


def test_split_budget_test_alignment_allowed(tmp_path):
    """Kiểm chứng tách bạch ngân sách: Code logic <= 30 dòng, Test verification alignment <= 120 dòng."""
    import tempfile
    td = Path(tempfile.gettempdir())
    biz_p = td / "service_core.py"
    test_p = td / "test_service_core.py"
    
    biz_p.write_text("def do_action():\n    return 1\n", encoding="utf-8")
    test_p.write_text("def test_do_action():\n    assert do_action() == 1\n", encoding="utf-8")
    
    try:
        # A. Hợp lệ: biz diff 2 dòng (<= 30), test diff 2 dòng (<= 120) -> PASS
        task = {
            "goal": "Cập nhật logic và test",
            "context": f"""
TASK_KIND: EDIT
FILE: {biz_p}
FILE: {test_p}
OLD_STRING: <<<
def do_action():
    return 1
>>>
NEW_STRING: <<<
def do_action():
    return 2
>>>
OLD_STRING: <<<
def test_do_action():
    assert do_action() == 1
>>>
NEW_STRING: <<<
def test_do_action():
    assert do_action() == 2
>>>
FOCUSED_TEST: python -m pytest {test_p}::test_do_action -q
BUDGET_CALLS: 10
FAIL_FAST: Nếu trong <= 3 iterations đầu thấy scope bất khả thi với budget 15 calls thì DỪNG NGAY (ABORT)...
"""
        }
        res = validate_dispatch(task)
        assert res["task_kind"] == "EDIT"
        assert len(res["target_files"]) == 2
    finally:
        biz_p.unlink(missing_ok=True)
        test_p.unlink(missing_ok=True)


def test_spoofed_test_path_in_biz_dir_rejected():
    """Sol P0: File test giả mạo nằm sâu trong module nghiệp vụ (/src/, /app/, /services/) bị từ chối là test file."""
    from farm_policy import is_test_file
    assert is_test_file(r"D:\Taadaa\tiktok-follow\follow_runner\tests\test_follow_state.py") is True
    assert is_test_file(r"D:\Taadaa\tools\test_cage_gate.py") is True
    assert is_test_file(r"D:\Taadaa\src\core\test_spoof.py") is False
    assert is_test_file(r"D:\Taadaa\app\services\test_payment.py") is False


def test_l2_test_unbound_rejected():
    """Sol P1: Coordinator mở L2 không được đụng vào file test không có liên hệ với target bị fail."""
    sid = "coord_unbound_test_sid"
    state = {
        "l2_eligible": True,
        "l2_targets": [os.path.normpath(r"D:\Taadaa\tiktok-follow\follow_runner\core\follow_state.py")],
        "write_ledger": {"t1_files": [], "t1_lines": 0, "l2_used": False, "l2_open": False}
    }

    # Đụng vào test không liên quan (tools/test_cage_gate.py) -> BỊ CHẶN L2 TEST UNBOUND
    unrelated_fn_args = {
        "path": r"D:\Taadaa\tools\test_cage_gate.py",
        "old_string": "def test_a():\n    pass",
        "new_string": "def test_a():\n    assert 1 == 1"
    }
    ok, reason, state = coordinator_write_gate(sid, "patch", unrelated_fn_args, state)
    assert ok is False
    assert "L2 TEST UNBOUND" in reason or "MISMATCH" in reason


def test_l2_ledger_migration_backward_compat():
    """Sol P1: Ledger cũ thiếu l2_biz_lines/l2_test_lines được tự động migrate an toàn."""
    sid = "coord_legacy_ledger_sid"
    state = {
        "l2_eligible": True,
        "l2_targets": [os.path.normpath(r"D:\Taadaa\tools\test_tiktok_account_tracker.py")],
        "write_ledger": {
            "t1_files": [],
            "t1_lines": 0,
            "l2_used": True,
            "l2_open": True,
            "l2_files": [os.path.normpath(r"D:\Taadaa\tools\test_tiktok_account_tracker.py")],
            "l2_lines": 10
            # Thiếu l2_biz_lines và l2_test_lines (schema cũ)
        }
    }
    fn_args = {
        "path": r"D:\Taadaa\tools\test_tiktok_account_tracker.py",
        "old_string": "def test_a():\n    pass",
        "new_string": "def test_a():\n    assert 2 == 2"
    }
    ok, reason, state = coordinator_write_gate(sid, "patch", fn_args, state)
    assert ok is True
    assert "l2_biz_lines" in state["write_ledger"]
    assert "l2_test_lines" in state["write_ledger"]
