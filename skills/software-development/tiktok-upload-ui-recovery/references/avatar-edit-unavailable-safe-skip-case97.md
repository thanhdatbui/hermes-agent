# Case 97: Safe-Skip AVATAR_EDIT_UNAVAILABLE Trên Secondary / Clone Profile

## Hiện tượng & Nguyên nhân
- Khi chạy batch upload video hoặc avatar (đặc biệt Row 5, các nick clone/phụ mới đăng nhập chung thiết bị), TikTok build mới hiển thị popup chặn sửa thông tin:
  `"hoạt động không có sẵn đối với tài khoản ban đầu"` (hoặc `"Activity unavailable for initial account"`).
- Trong `scripts/tiktok_workflow/state_machine.py`, hàm `_is_avatar_edit_unavailable` phát hiện `edit_state == "unavailable"`.
- Trước đây code raise `WorkflowError("AVATAR_EDIT_UNAVAILABLE")`, làm nổ phiên `FAILED` và crash toàn bộ máy trong batch (ví dụ nổ 14 máy cùng lúc).

## Nguyên tắc xử lý (Safe-Skip)
- Khi phát hiện `edit_state == "unavailable"`:
  1. Đóng popup: Gọi `adapter._tap_if_found(current_xml, text="OK")` hoặc `adapter.back()`.
  2. Ghi log cảnh báo: `[ENSURE_AVATAR] TikTok báo hoạt động sửa avatar không có sẵn trên profile phụ; safe-skip để tiếp tục flow`.
  3. Ghi nhận `self.context.avatar_status = "SKIPPED_AVATAR_EDIT_UNAVAILABLE"` (hoặc `SKIPPED_EXISTING_AVATAR`).
  4. Trả về `True` để cho phép luồng tiếp tục sang các bước tiếp theo (đăng video, release lease) mà không làm FAILED batch.
- Tập hợp `accepted` avatar status tại `_handle_ensure_avatar` bắt buộc phải chứa `"SKIPPED_AVATAR_EDIT_UNAVAILABLE"` để vượt qua verification gate.
