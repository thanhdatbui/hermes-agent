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
  - Nếu là video #1 và có file avatar hợp lệ -> thực hiện upload avatar và ghi nhận kết quả.
  - Nếu là video #2+ hoặc không yêu cầu avatar -> skip an toàn và chuyển tiếp sang `DELETE_REMOTE_MEDIA`.
