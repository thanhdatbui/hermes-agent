# POST_NEXT_SELECTOR_EXHAUSTED & Preview Surface sp3 Recovery

## 1. Dấu hiệu nhận diện (Error Signature)
- Log văng lỗi:
  `[FAILED] [POST_NEXT_SELECTOR_EXHAUSTED] POST: final composer/editor Next surface was not confirmed`
- Hiện trường thiết bị:
  - Màn hình đang ở chế độ xem trước video (Preview/Editor).
  - Header tiêu đề: `"Xem trước"` (`resource-id="com.ss.android.ugc.trill:id/rzu"`).
  - Góc dưới bên phải có nút Đăng hình viên thuốc màu đỏ/hồng:
    - `text="Đăng"` hoặc `content-desc="Đăng"`
    - `resource-id="com.ss.android.ugc.trill:id/sp3"`
    - `class="android.widget.Button"`, clickable=true.
  - Caption/hashtag đã được điền sẵn trên màn hình preview.

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Thiếu Selector `sp3`**:
   - Trong `state_machine.py` (`_handle_post`), danh sách resource-id của nút Post chỉ bao gồm:
     `("sh8", "shd", "sox", "soz", "sp7", "rbp", "t66", "post_action", "post_button")`
   - Bản TikTok mới sử dụng `id/sp3` cho nút Đăng trên màn hình preview.
2. **Không có nút Next/Tiếp trên màn hình Preview**:
   - Luồng upload truyền thống tìm nút "Tiếp" (Next) để chuyển từ Editor sang Post Composer.
   - Khi TikTok hiển thị thẳng màn hình Preview với nút "Đăng" ở góc dưới bên phải, không có nút "Tiếp". Bộ dò tìm Next bị cạn selector (`POST_NEXT_SELECTOR_EXHAUSTED`) và fail flow thay vì bấm nút Đăng sẵn có.
3. **Receipt Idempotency Race / Stale File**:
   - `_record_post_intent` dùng `path.open("x")`. Nếu có file receipt cũ từ ngày/lần chạy trước chưa dọn (`machine_X_account_Y_video_Z.json`), lệnh sẽ văng `FileExistsError` và từ chối tap Đăng.

## 3. Quy chuẩn sửa đổi (Patch Pattern trong state_machine.py)
1. **Bổ sung `sp3` vào tất cả các tuple resource-id của Post Button**:
   - `("sh8", "shd", "sox", "soz", "sp7", "sp3", "rbp", "t66", ...)`
2. **Mở rộng nhận diện bề mặt Preview / "Xem trước"**:
   - Kiểm tra `("Xem trước" in xml_text or "rzu" in xml_text or "sp3" in xml_text)` kết hợp tìm selector `resource_id="sp3"`, `text="Đăng"`, `content_desc="Đăng"`.
3. **Bypass `POST_NEXT_SELECTOR_EXHAUSTED` khi đã ở Preview**:
   - Trước khi raise `POST_NEXT_SELECTOR_EXHAUSTED`, kiểm tra nếu màn hình chứa marker Preview/Đăng (`Xem trước`, `rzu`, `sp3`, `Đăng`, `Post`), thử tap trực tiếp nút Đăng (`sp3` hoặc text/desc "Đăng").
   - Nếu tap thành công: gọi `self._mark_post_surface_recovery_retrying()` và return `self._finish_single_post_tap(adapter)`.
4. **Xử lý `FileExistsError` trong `_record_post_intent`**:
   - Khi bắt `FileExistsError`, đọc `old_payload`. Nếu `old_run_id != current_run_id`, ghi đè atomic bằng `_write_post_attempt_receipt(payload)` thay vì dừng khẩn cấp.
