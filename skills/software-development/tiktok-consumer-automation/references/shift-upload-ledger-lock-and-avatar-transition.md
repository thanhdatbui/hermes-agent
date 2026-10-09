# Shift Upload Ledger Lock Contention & Video #1 Avatar Transition Guidelines

## 1. Shift Upload Ledger Lock Contention Fix (Case 65)

### Problem / Anti-Pattern
- Khi 50+ máy kết thúc feed đồng thời ở cuối ca và cùng gọi upload hook, tất cả cùng tranh chấp một file lock duy nhất `.shift_upload_history.lock` (`_ShiftUploadLedger`).
- Hardcode timeout ngắn (10s) cùng vòng lặp retry cố định `0.05s` gây hiện tượng *thundering herd*, khiến các máy xếp hàng sau bị timeout (`shift_upload_lock_timeout_fail_closed`), bị watchdog xếp nhầm vào `Timeout/Quá giờ`.

### Resolution Pattern
1. **Adaptive Timeout & Jitter:**
   - Nâng timeout `_InterProcessFileLock` lên `60.0s`.
   - Bổ sung randomized jitter `random.uniform(0.02, 0.08)` và clamp khoảng sleep vào thời gian còn lại: `time.sleep(min(remaining, jitter))`.
2. **Zero-Timeout Non-Blocking Support:**
   - `timeout=0.0` thực hiện 1 lần thử non-blocking (`LOCK_NB` / `LK_NBLCK`). Nếu không vướng tranh chấp thì acquire thành công ngay lập tức; nếu vướng tranh chấp thì fail promptly mà không chờ.
3. **Hard Deadline Monotonic Propagation:**
   - Tiếp nhận `_hard_deadline_monotonic` từ session config.
   - Kiểm tra deadline nghiêm ngặt trước khi acquire lock, sau khi có lock, trong vòng lặp scan report, và trước khi thực hiện atomic file replace.
   - Bất kỳ khi nào quá hạn deadline, fail-closed ngay lập tức mà không làm bẩn (mutate) trạng thái ledger.
4. **Atomic Ledger Commit & Ground-Truth Caching:**
   - Ghi ledger qua temp file `f".shift_upload_history.{uuid.uuid4().hex}.tmp"` rồi `os.replace()`.
   - Khi tìm thấy report ground-truth thành công trong `CodexRuntime`, ghi nhận `status: "success"` với `source: "codex_runtime_ground_truth"` vào ledger để các lần tra cứu sau đạt tốc độ O(1) mà không cần scan lại ổ đĩa.

---

## 2. TikTok Video Workflow Transition: Video #1 Avatar Hook

### Problem / Anti-Pattern
- Trong `scripts/tiktok_workflow/state_machine.py`, `TRANSITION_MAP` vô tình cấu hình sau `UPDATE_WORKBOOK` nhảy thẳng sang `DELETE_REMOTE_MEDIA`, bỏ qua `ENSURE_AVATAR`.
- Kết quả: Máy đăng video #1 (lần đầu đăng video) hoàn thành post và cập nhật workbook nhưng không thực hiện đổi avatar (`avatar_status: None`).

### Resolution Pattern
- Đảm bảo `TRANSITION_MAP` của workflow đăng video:
  ```python
  WorkflowState.UPDATE_WORKBOOK: (
      WorkflowState.ENSURE_AVATAR,
      WorkflowState.DELETE_REMOTE_MEDIA,
      WorkflowState.SUCCESS,
      WorkflowState.FAILED,
      WorkflowState.MANUAL_REVIEW,
  )
  ```
- Hàm `_ensure_avatar()` sẽ tự động kiểm tra `_force_avatar_upload_allowed()`:
  - Nếu là video #1 (`video_number == 1`) và có file avatar hợp lệ -> thực hiện upload avatar và ghi nhận kết quả.
  - Nếu là video #2+ hoặc không yêu cầu avatar -> skip an toàn và chuyển tiếp sang `DELETE_REMOTE_MEDIA`.
  - **Pitfall nick bị lỡ avatar ở Video #1**: Khi nick đã đăng video 1 thành công nhưng vì lý do nào đó chưa đổi avatar (vẫn còn placeholder icon camera trên UI), các ca nuôi sau (`video_number > 1`) sẽ tự động bypass hook này. Hệ thống KHÔNG có cột đánh dấu trạng thái avatar trong Excel (`TikN.xlsx`, `taikhoan_run_safe.xlsx`). Để bù avatar cho nick đã qua mốc Video 1, BẮT BUỘC dùng launcher độc lập:
    `powershell.exe -File run_tiktok_upload_avatar.ps1 -Tik <N> -ForceAvatarMachineList "<may>"`
    Khi đó launcher truyền flag `--avatar-smoke` và `--force-avatar-machines`, ghi nhận kết quả tại `report.json` (`status: AVATAR_SMOKE_SUCCESS`, `avatar_status: FORCED_REPLACED_VERIFIED`).

---

## 3. Granular Subprocess Upload Error Extraction & Telegram HTML Escaping

### Problem / Anti-Pattern
- Khi tiến trình con đăng video (`run_post.py`) thất bại (`proc.returncode != 0`), gán cứng fallback `upload_subprocess_nonzero` làm mất toàn bộ ngữ cảnh chẩn đoán trong `report.json`, `stderr`, và `stdout`.
- Đưa các chuỗi động (`error_reason`, `account`, `serial`, `status_text`) trực tiếp vào template Telegram HTML mà không bọc `html.escape()`. Khi thông báo lỗi chứa ký tự đặc biệt như `<redacted>` (từ secret filter) hoặc `<module>`, Telegram Bot API từ chối gửi do lỗi cú pháp HTML (`can't parse entities`).

### Resolution Pattern
1. **Bóc tách lỗi đa tầng (`_extract_upload_subprocess_error`):**
   - **Tầng 1 (`report.json`):** Đọc `err = rep_data.get("error") or rep_data.get("reason")`, `last_st = rep_data.get("last_state")`, `rep_st = rep_data.get("status")`. Nếu có `err`, chuẩn hóa khoảng trắng và thêm tiền tố `[last_st]` (nếu `last_st` chưa có trong chuỗi lỗi). Nếu chỉ có `last_st`, dùng `failed_at_state_{last_st}`. Nếu có `rep_st != "SUCCESS"`, dùng `upload_status_{rep_st}`.
   - **Tầng 2 (`stderr`):** Nếu `stderr.strip()`, lấy dòng lỗi cuối cùng không rỗng (thường là Traceback / Exception type).
   - **Tầng 3 (`stdout`):** Quét ngược tìm dòng chứa `[ERROR]` hoặc `[CRITICAL]` gần nhất, hoặc dòng trạng thái cuối cùng `>>> State: <state>`.
   - **Tầng 4 (Fallback):** `upload_exit_code_{proc.returncode}`.
   - **Giới hạn độ dài:** Cắt ngắn chuỗi lỗi ở tối đa 250 ký tự để tin nhắn cảnh báo súc tích và không tràn layout.
2. **Bảo vệ ký tự HTML trong Alert Telegram:**
   - Trong `send_farm_machine_alert` và `send_farm_script_alert` (`automation_core/alerts.py`), luôn thực hiện:
     ```python
     import html
     safe_account = html.escape(str(account or ""))
     safe_serial = html.escape(str(serial or "N/A"))
     safe_error_reason = html.escape(str(error_reason or ""))
     safe_status_text = html.escape(str(status_text or ""))
     ```
   - Chèn các biến `safe_*` vào caption/template HTML thay cho chuỗi thô.

