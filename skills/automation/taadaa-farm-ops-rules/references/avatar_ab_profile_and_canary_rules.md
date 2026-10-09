# Kỷ luật Up Avatar & Xử lý A/B Profile Layout (TikTok 47.x+)

## 1. Chống Fake-Done khi đổi Avatar (Canary Enforcement)
- Khi user phát lệnh "đổi avatar", tuyệt đối **CẤM** chỉ set Excel `Avatar = OK` hoặc chạy avatar-smoke để nhận `SKIPPED_EXISTING_AVATAR` rồi báo xong.
- Yêu cầu bắt buộc:
  * Phải chạy canary với cờ `--force-avatar-upload` để ép tải ảnh mới lên điện thoại thật.
  * Báo hoàn tất bắt buộc đính kèm `MEDIA:` chụp màn hình Profile thật trên máy chứng minh ảnh avatar MỚI đã được cập nhật thành công.

## 2. Quy tắc bắt đúng hiện trường lỗi (True Screen Capture)
- Khi nghi ngờ hoặc gặp lỗi giao diện kẹt:
  * Phải chụp ngay màn hình máy thật tại chính xác khoảnh khắc bị kẹt, đúng tài khoản mục tiêu.
  * CẤM tự ý bấm mò vào các nút/tài khoản khác làm kích hoạt popup lỗi nền tảng (ví dụ: "Hoạt động không có sẵn") rồi đổ lỗi cho thiết bị.
  * Nếu xuất hiện pop-up lỗi, phải cung cấp ảnh màn hình ngay trước khi pop-up mở ra để chứng minh nguyên nhân thực tế.

## 3. Đặc thù A/B Testing giao diện Profile TikTok (v47.x+)
- Một số nick bị áp giao diện mới:
  * Không có nút dạng chữ `[ Sửa hồ sơ ]` to.
  * Node tên hiển thị gộp chung cả chữ và icon bút chì, khi tap vào lại mở sheet chuyển đổi tài khoản thay vì sửa hồ sơ.
  * Nút phụ: Nút chia sẻ / 3 chấm `[880..1040, 630..740]` nằm bên phải `+ Thêm tiểu sử`.
- Khi viết/sửa detector trong `state_machine.py`:
  * Bổ sung layout detector cho `share_profile_button` hoặc icon menu phụ để mở được màn hình hồ sơ tương ứng.
  * Sau khi sửa bắt buộc chạy unit tests liên quan (`test_avatar_edit_and_milestone.py`) và commit với tiền tố `[L2-surgery]`.
