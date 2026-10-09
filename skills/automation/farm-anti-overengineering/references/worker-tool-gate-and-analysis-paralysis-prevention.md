# Worker Tool Gate & Chống Analysis Paralysis (06/09/2026)

## 1. Sự Cố Thực Tế: 3 Worker, 105 Turns, 2 Triệu Token và 107 Phút
Ngày 06/09/2026, khi xử lý Farm Alert [MÁY 9] (`failed_dismiss_overlay_before_navigation: follow_friends_popup_no_close_control`), hệ thống bị ngâm gần 2 tiếng do 3 điểm nghẽn:
1. **Worker 1 & 2 (72 phút):** Mắc hội chứng Analysis Paralysis — liên tục đọc XML, so khớp từng marker, tìm kiếm phân tích root cause từ đầu qua 35 turns mà KHÔNG hề ghi 1 dòng code nào xuống đĩa. Chạm trần `max_iterations = 35` 2 lần liên tiếp.
2. **Coordinator Dispatch Mù:** Không truyền `WORK_PACKAGE` có vị trí hàm và ý định vá cụ thể (`patch_intent`), đẩy toàn bộ gánh nặng tìm hiểu từ con số 0 cho worker.
3. **Stale Device Lock & PYTHONPATH:** Canary bị nghẽn do file lock cũ (`machine_9.lock.json` của PID 179800 đã chết) và biến `$env:PYTHONPATH` rò rỉ từ venv Hermes Agent gây lỗi binary `PIL._imaging`.

---

## 2. Giải Pháp Kiến Trúc: WorkerToolGate (Plugin `farm-coordinator-guard` v2.1)
Thay vì trông chờ vào LLM tự giác, cưỡng chế bằng code cứng tại `pre_tool_call`:

```python
WORKER_STATES: Dict[str, Dict[str, int]] = {}

def check_worker_tool_gate(tool_name: str, session_id: str) -> Optional[Dict[str, Any]]:
    """Cưỡng chế cứng đối với Worker subagents để triệt tiêu Analysis Paralysis."""
    if not session_id:
        return None
    state = WORKER_STATES.setdefault(session_id, {"read_count": 0, "write_count": 0, "call_count": 0})
    state["call_count"] += 1

    READ_TOOLS = {"read_file", "search_files"}
    WRITE_TOOLS = {"write_file", "patch"}

    if tool_name in READ_TOOLS:
        # Rule 1: Hết ngân sách đọc (READ_BUDGET = 3)
        if state["read_count"] >= 3:
            return {
                "action": "block",
                "reason": (
                    f"⛔ [WORKER TOOL GATE - READ BUDGET EXHAUSTED]: "
                    f"Ngân sách đọc của Worker đã hết ({state['read_count']}/3). "
                    "Bạn BẮT BUỘC phải gọi write_file hoặc patch ngay bây giờ theo patch_intent! "
                    "CẤM tiếp tục khảo sát lan man."
                ),
            }
        # Rule 2: Hạn chót ghi code (WRITE_DEADLINE = 4)
        if state["call_count"] >= 4 and state["write_count"] == 0:
            return {
                "action": "block",
                "reason": (
                    f"⛔ [WORKER TOOL GATE - WRITE DEADLINE]: "
                    f"Đã qua {state['call_count'] - 1} tool calls mà chưa có thao tác write_file/patch nào. "
                    "Mọi công cụ đọc đã bị KHÓA CỨNG. Bạn BẮT BUỘC phải ghi bản vá (write_file/patch) ngay lập tức!"
                ),
            }
        state["read_count"] += 1

    elif tool_name in WRITE_TOOLS:
        state["write_count"] += 1

    return None
```

---

## 3. Quy Chuẩn Hợp Đồng WORK_PACKAGE Cho Coordinator
Coordinator BẮT BUỘC phải cung cấp đủ các trường sau trong `context` khi gọi `delegate_task`:
```text
[WORK_PACKAGE]:
- Alert: [MÁY N] <error_symbol>
- Target: File <path>, function <name>, line hint <approx_line>
- Root Cause Hint: Màn hình kẹt gì, vì sao handler không match hoặc false positive.
- Patch Intent:
  + Strategy: <early_return_guard | timeout_adjustment | etc.>
  + Pseudocode / logic: if is_main_feed and not has_dialog: return False
- Ràng buộc:
  + Turn 1: Đọc đúng vị trí dòng code
  + Turn 2: Patch file ngay lập tức
  + Turn 3: py_compile và verify
```
**CẤM TUYỆT ĐỐI dispatch khi chưa có `Patch Intent`.**

---

## 4. Tự Động Hóa Pre-flight Canary (Stale Lock & PYTHONPATH)
Trong mọi script runner PowerShell (`run-feed-session.ps1`, v.v.):
1. **Cô lập PYTHONPATH:** Đặt `$env:PYTHONPATH = ""` ở đầu file để triệt tiêu xung đột binary DLL/SO giữa các venv.
2. **Tự dọn Stale Device Lock:** Trước khi chạy, kiểm tra `$env:USERPROFILE\.codex\device-locks\machine_${m}.lock.json`. Nếu PID không tồn tại (`Get-Process -Id $pid -ErrorAction SilentlyContinue` trả về rỗng), tự động xóa file lock (`Remove-Item -Force $lockPath`).
