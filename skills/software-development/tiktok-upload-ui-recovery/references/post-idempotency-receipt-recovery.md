# Post Idempotency Receipt Recovery & Crash Fix

## Vấn đề: `upload_subprocess_nonzero` khi chạy lại hoặc retry

### Dấu hiệu nhận diện trong `execution.log`:
```text
RuntimeError: Post tap already recorded for this machine/video; refusing duplicate post tap to avoid double-posting
```
Subprocess Python kết thúc với exit code non-zero, khiến batch runner phân loại job là `upload_subprocess_nonzero`.

---

## Nguyên nhân gốc rễ (Root Cause)
1. Trong lần upload trước, attempt đã tap nút Post và lưu receipt idempotency dạng `machine_<M>_account_<A>_video_<V>.json` với status `post_tapped` hoặc `verification_pending`.
2. Khi retry hoặc rerun tiến trình, `_handle_post()` gọi `_assert_post_attempt_safe_to_tap()` và quăng unhandled `RuntimeError` để ngăn double-post. Việc quăng lỗi này làm sập toàn bộ flow thay vì chuyển giao sang bước xác minh.

---

## Giải pháp & Quy chuẩn Codebase

### 1. Graceful Transition sang `VERIFY_POST`
Trong `scripts/tiktok_workflow/state_machine.py`:
- `_handle_post()` nạp receipt bằng `_load_post_attempt_receipt()`.
- Nếu receipt đã tồn tại và chưa được authorize retry:
  - Ghi nhận `post_tap_attempted = True`.
  - Không tap nút Post lần 2.
  - Return `True` để workflow tiếp tục sang `VERIFY_POST`.
  - `VERIFY_POST` sẽ kiểm tra lại các UI indicator / scan lại grid profile để xác nhận video đã được đăng thành công hay chưa.

### 2. Schema Receipt & Account Matching
- Cho phép `machine` và `video_number` linh hoạt kiểu dữ liệu.
- `_receipt_matches_target_account()`: Phải so khớp chính xác với `target_account` của job hiện tại để tránh việc receipt của account cũ trên cùng máy vật lý chặn account mới.

### 3. Media Fingerprint Stale Reservation Gate
- `MediaFingerprintLedger.reserve()`: Nếu tiến trình trước bị ngắt (timeout/kill) khi chưa finalize, reservation ở trạng thái `reserved` sẽ chặn các lần chạy lại trong 30 phút (`stale_after_seconds = 1800`).
- Khi chạy canary test hoặc live run qua terminal, luôn đặt `timeout >= 600s` để tránh bị kill ngang giữa chừng.
