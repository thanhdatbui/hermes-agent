# Avatar Edit Unavailable Safe-Skip Contract

## Bối cảnh
Khi upload video hoặc chạy flow `ENSURE_AVATAR` trên các profile phụ (sub-accounts), TikTok có thể hiển thị dialog thông báo hoạt động sửa avatar không có sẵn:
- `edit_state == "unavailable"`
- Dialog có nút `OK` hoặc yêu cầu `adapter.back()` để dismiss.

## Contract xử lý (Safe-Skip)
Trước đây, hệ thống raise `WorkflowError("AVATAR_EDIT_UNAVAILABLE")` làm đứt toàn bộ flow upload video của tài khoản phụ.
Contract safe-skip yêu cầu:
1. Dismiss dialog: `adapter._tap_if_found(current_xml, text="OK")` hoặc fallback `adapter.back()`.
2. Ghi warning log: `"[ENSURE_AVATAR] TikTok báo hoạt động sửa avatar không có sẵn trên profile phụ; safe-skip để tiếp tục flow"`.
3. Đặt trạng thái context an toàn: `self.context.avatar_status = "SKIPPED_EXISTING_AVATAR"` và return `True`.
4. Mở rộng tập hợp `accepted` avatar status để bao gồm cả `SKIPPED_AVATAR_EDIT_UNAVAILABLE` phòng trường hợp gán trực tiếp:
   ```python
   accepted = {
       "SKIPPED_EXISTING_AVATAR",
       "UPLOADED_VERIFIED",
       "FORCED_REPLACED_VERIFIED",
       "SKIPPED_AVATAR_EDIT_UNAVAILABLE",
   }
   ```
5. Viết unit test xác nhận adapter dismiss dialog, không ném exception và flow tiếp tục bình thường.
