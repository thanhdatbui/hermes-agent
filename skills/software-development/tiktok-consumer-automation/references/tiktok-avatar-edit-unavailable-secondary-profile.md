# TikTok Avatar Edit Unavailable Handling on Secondary Profile

## Problem
Khi tài khoản TikTok là profile phụ / clone chuyển đổi từ account switcher ("chuyển đổi tài khoản"), TikTok có cơ chế bảo vệ chặn đổi avatar:
- Xuất hiện popup cảnh báo: *"Hoạt động không có sẵn đối với tài khoản ban đầu"* (hoặc text tương đương trong UI).
- Hệ thống nhận diện qua `_is_avatar_edit_unavailable` khi `wait_for_avatar_edit_screen` trả về state `"unavailable"`.

## Pitfall
Trước đây, state machine cố gắng fallback mở profile edit qua avatar circle hoặc deeplink rồi raise:
```python
raise WorkflowError(
    WorkflowState.ENSURE_AVATAR,
    "TikTok báo hoạt động sửa avatar không có sẵn",
    "AVATAR_EDIT_UNAVAILABLE",
)
```
Việc raise `WorkflowError` khiến máy bị fail cả batch (status `FAILED`), làm gián đoạn toàn bộ tiến trình upload video tiếp theo chỉ vì một tác vụ phụ (ensure avatar) bị TikTok chặn logic tài khoản phụ.

## Rule & Safe-Skip Contract
1. Khi `edit_state == "unavailable"` (đã detect dialog thông báo không có sẵn):
   - Đóng dialog: Tap nút `"OK"` nếu có, hoặc gửi phím `adapter.back()`.
   - Ghi nhận trạng thái: Set `self.context.avatar_status = "SKIPPED_AVATAR_EDIT_UNAVAILABLE"`.
   - Log cảnh báo `logger.warning(...)` thay vì raise `WorkflowError`.
   - Return `True` để luồng upload video chính tiếp tục chạy bình thường.
2. Thêm `"SKIPPED_AVATAR_EDIT_UNAVAILABLE"` vào tập hợp `accepted` tại `_handle_ensure_avatar`:
   ```python
   accepted = {
       "SKIPPED_EXISTING_AVATAR",
       "UPLOADED_VERIFIED",
       "FORCED_REPLACED_VERIFIED",
       "SKIPPED_AVATAR_EDIT_UNAVAILABLE",
   }
   ```
   Điều này đảm bảo sau khi return `True`, step hậu kiểm không đánh dấu `[AVATAR_VERIFY_FAILED]` hoặc `FINAL_BLOCKED`.
