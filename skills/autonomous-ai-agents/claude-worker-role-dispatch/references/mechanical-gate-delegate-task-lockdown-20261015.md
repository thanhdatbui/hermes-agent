# Mechanical Gate Dispatch Lockdown: haiku_worker.py & ag_cli.py vs delegate_task

## 1. Bối cảnh sự cố & Vấn đề gốc rễ (15/10/2026)

### Sự cố
Khi Operator yêu cầu *"R làm đi"* sau khi thảo luận giải pháp code, Coordinator (Hermes LLM) đã vô thức gọi tool `delegate_task` (`TASK_KIND: EDIT`).
Hậu quả:
- Subagent `omni-worker` (trỏ vào cụm Gemini Pool `:20129`) khởi động chậm chạp.
- Chạy lặp đi lặp lại 15 tool calls, ngốn tới **211.53 giây (> 3.5 phút)** cho một bản vá O(1) chỉ sửa 4 dòng code.
- Làm loãng context, gây ức chế cho Operator khi trước đó đã thống nhất dùng `haiku_worker.py` (chạy 6–15s).

### Root Cause: Tại sao "Prompt Kỷ Luật" Luôn Thất Bại?
1. **Prompt Drift & Context Attenuation:** Khi hội thoại dài hoặc sau khi nén context, các chỉ thị mềm trong system prompt bị suy giảm trọng số chú ý.
2. **Contradictory Instructions trong Prompt:** Trong System Prompt cũ của session vẫn còn câu lệnh:
   `"+ T2 (Thi công lớn > 15 dòng hoặc kiến trúc lõi): BẮT BUỘC dispatch worker qua delegate_task (Model: ag-gemini-pool-3)..."`
   Câu lệnh này trực tiếp triệt tiêu rule mới trong Memory/User Profile (`"Worker: Haiku 5.5 CLI chính, AG CLI Pro dự phòng"`).
3. **Nguyên lý kiến trúc:** Bất kỳ quy tắc nào chỉ nhắc nhở bằng prompt ("should") mà không có chốt chặn vật lý ("must/block") thì trước sau gì Coordinator cũng sẽ vi phạm.

---

## 2. Giải Pháp Khóa Cứng (Mechanical Gate) trong Dispatch Contract Hook

Thay vì trông chờ vào sự "tự giác" của model, chốt chặn được dời xuống tầng **Hook Pre-Tool-Call vật lý** (`guard_dispatch_contract.py`).

### Logic Chặn Cứng
Tại nhánh `is_code_edit` (phát hiện có nhãn `FILE:`, `OLD_STRING`, `NEW_STRING` hoặc động từ sửa code), Hook kiểm tra:
```python
# HARD GATE #3 - MECHANICAL BLOCK: Code edits via delegate_task are forbidden
# unless explicitly overridden with ALLOW_SUBAGENT_CODE_EDIT or OVERRIDE_SUBAGENT_DISPATCH
if is_code_edit:
    has_override = bool(re.search(
        r'\b(?:ALLOW_SUBAGENT_CODE_EDIT|OVERRIDE_SUBAGENT_DISPATCH|WORKER_CLI_EXHAUSTED|HAIKU_AND_AGY_FAILED)\b',
        combined,
        re.IGNORECASE
    ))
    if not has_override:
        msg = (
            f"[HARD GATE #3 - CODE EDIT DISPATCH BLOCKED] delegate_task BỊ CẤM CHO TASK SỬA CODE! "
            f"Bắt buộc thi công qua haiku_worker.py (6-15s O(1)). CẤM dùng delegate_task!"
        )
        _log_dispatch_audit("block", "subagent_edit_blocked", msg)
        print(json.dumps({"action": "block", "message": msg}))
        sys.exit(0)
```

---

## 3. Bậc Thang Cứu Hộ 3 Tầng (3-Tier Worker Hierarchy)

1. **Tier 1 (Mặc định chính):**
   - Lệnh: `python D:/Taadaa/tools/haiku_worker.py "<instruction>" --file "<target_file>"`
   - Model: Claude Haiku 5.5 CLI (`claude -p`).
   - Thời gian thi công: 6 – 15s ($O(1)$), cực rẻ token.

2. **Tier 2 (Tự động chuyển tầng bên trong `haiku_worker.py`):**
   - Kích hoạt khi:
     * Quota 5h $\ge 85\%$ hoặc Weekly $\ge 90\%$.
     * File `plan-usage-history.json` bị lỗi đọc hoặc stale $>72$h.
     * Runtime phát hiện lỗi chạm trần session (`hit your session limit`, `hit your limit`, `resets at`...).
   - Hành động tự động: Gọi `python D:/Taadaa/tools/ag_cli.py fix` (Antigravity CLI Pool 7 accounts Pro).

3. **Tier 3 (Khi CẢ HAI Haiku và AG CLI đều thất bại):**
   - **Nhánh A (Task nhỏ O(1) <= 2 files, <= 30 dòng diff):**
     Coordinator kích hoạt **L2 Emergency Surgery**, tự sửa trực tiếp trong session chính, commit với tiền tố `[L2-surgery]`.
   - **Nhánh B (Task thi công lớn vượt ngân sách L2):**
     Được phép dispatch `delegate_task` bằng cách kẹp cờ ngoại lệ:
     `WORKER_CLI_EXHAUSTED: true` hoặc `HAIKU_AND_AGY_FAILED: true`
     kèm theo bằng chứng log lỗi của cả 2 CLI. Hook sẽ nhận diện cờ này và tự động mở van cho subagent chạy qua.
