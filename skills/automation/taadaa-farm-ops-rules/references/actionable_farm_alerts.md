# Actionable Farm Alert Contract & Architecture (v3.0 - Claude Opus High Hard-Enforcement)

## 1. Cấu trúc Actionable Alert Contract (chuẩn hóa 2026-09-06 sau sự cố Máy 14)
Khi bất kỳ script nào trên Farm (Feed, Follow, Reg, 2FA...) phát sinh lỗi dừng máy, alert gửi về Telegram group BẮT BUỘC dùng format Actionable Payload đã được phân loại (Classified), **CẤM TUYỆT ĐỐI trỏ vào file monolith flow** (`*_smoke.py`, >20k dòng) gây bẫy analysis paralysis:

```text
🚨 [FARM ALERT: MÁY <N>] DỪNG PHIÊN — CLASS=<POPUP_ALLOWLIST | SELECTOR_DRIFT | NAV_ROUTING | AUTH>
• Máy: <N> | Serial: <serial> | Nick: <account>
• Quy trình: <process_name> (<repo_name>)
• Symptom(code): <error_reason_code> (<chi_tiết_ngắn_gọn>)
• Hiện trường: ĐANG MỞ (Lock 1h active)

━━━━━━━━━ PATCH_CONTRACT (mechanical — hook & coordinator đọc block này) ━━━━━━━━━
CLASS: <POPUP_ALLOWLIST | SELECTOR_DRIFT | NAV_ROUTING | AUTH>
ALLOWED_FILES: <đường_dẫn_file_nhẹ_đích_danh_ví_dụ_benign_popup_registry.py>
FORBIDDEN_FILES: **/flows/*_smoke.py     ← MONOLITH: CẤM READ, CẤM EDIT
CHANGE_TYPE: <register_one_entry | update_one_selector | fix_one_route | fix_one_branch>
BUDGET: max_tool_calls=12 ; wall_clock=5m ; read_gate=3
EVIDENCE (đọc TỐI ĐA 2-3 file dưới, CẤM mở flow để "hiểu thêm"):
  1. summary : <đường dẫn file summary.txt>
  2. registry: <ALLOWED_FILES>
  3. dump    : <đường dẫn file UI XML nếu có>
CANARY (B4): powershell.exe -ExecutionPolicy Bypass -File "<script_canary>" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
CLOSEOUT (B5): 6 Gate standard (G0 Canary Live Evidence -> G1 Docs -> G2 Commit -> G3 Rebase -> G4 Push)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 2. Quy tắc cho Agent / Coordinator khi nhận Alert
1. **Tuyệt đối không quét đĩa / grep mò mẫm**: Tin nhắn alert đã chứa sẵn `ALLOWED_FILES` và `EVIDENCE`. Không dùng `grep -rn`, `find`, `os.walk` hay `search_files` diện rộng.
2. **CẤM GIAO GOAL MỞ KHI ALERT ĐÃ CÓ PATCH_CONTRACT**:
   - Khi alert thuộc class `POPUP_ALLOWLIST` hoặc `SELECTOR_DRIFT`, Coordinator **bắt buộc copy nguyên khối PATCH_CONTRACT** vào `goal` và `context` khi gọi `delegate_task`.
   - CẤM dispatch worker với goal chung chung như *"Điều tra root cause và sửa code"*, tránh đẩy worker vào vòng xoáy 35 tool calls đọc lan man.
3. **Quy trình 5 bước khép kín (Action Gate)**:
   - **B1 (Inspect O(1))**: Chạy đúng 1 lệnh `python D:/Taadaa/tools/inspect_machine.py <N>` để nắm focus và trạng thái ADB.
   - **B2 (Dispatch ngay)**: Khóa scope và dispatch Worker kèm `PATCH_CONTRACT`.
   - **B3 (Worker Patch)**: Worker chỉ được đọc tối đa 3 lần (`READ_BUDGET=3`), turn 4 bắt buộc ghi đĩa vào `ALLOWED_FILES`, kiểm tra `py_compile`.
   - **B4 (Canary Test)**: Kích hoạt lệnh Canary được chỉ định trong alert (<30s).
   - **B5 (Closeout)**: Báo cáo kết quả và chốt phiên 6 Gate.

## 3. Quy tắc cho Developer / Alert Generator khi gọi `send_farm_machine_alert`:
Bắt buộc phân loại `symptom_code` trước khi sinh alert; trỏ `ALLOWED_FILES` vào registry hoặc sub-module nhẹ, **CẤM TUYỆT ĐỐI truyền `flow_file` là các file monolith `*_smoke.py`**:
```python
ROUTES = {
    "POPUP_NOT_IN_ALLOWLIST": (
        "POPUP_ALLOWLIST",
        r"D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/benign_popup_registry.py",
        "register_one_entry",
    ),
    "SELECTOR_NOT_FOUND": (
        "SELECTOR_DRIFT",
        r"D:/Taadaa/tiktok-luot nuoi acc/python_runner/core/selectors.py",
        "update_one_selector",
    ),
}
``` -SkipAccountWorkbookSync -Run',
)
```
