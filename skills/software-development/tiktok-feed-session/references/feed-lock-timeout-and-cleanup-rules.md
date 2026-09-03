# Quy tắc Device Lock & Cleanup khi lỗi Farm Nuôi TikTok

## 1. Thời gian Timeout Phiên Nuôi
- Cấu hình `DEFAULT_DEVICE_TIMEOUT_SECONDS = 1500.0` (25 phút / máy).
- Đảm bảo các máy mạng lag, tải video chậm hoặc qua nhiều bước kiểm tra trung gian không bị ngắt ngang phiên nuôi.

## 2. Giới hạn TTL Khóa Lock khi lỗi (2 giờ)
- Lỗi tự động phát sinh trong quá trình chạy nuôi (`status="blocked"`) chỉ giữ lock tối đa **2 giờ** (`DEFAULT_BLOCKED_LOCK_MAX_AGE_SECONDS = 7200.0`).
- Sau 2 giờ, nếu không có can thiệp thủ công từ user/agent, cơ chế handoff tự động coi lock hết hạn và nhả máy để turn nuôi sau tiếp tục chạy, tránh treo farm vĩnh viễn (`skipped-device-locked`).
- Chỉ có lệnh khóa chủ động bằng tay từ user mới được phép giữ lock vô thời hạn.

## 3. Quy tắc Giữ hiện trường vs Cleanup khi lỗi
- Khi phiên nuôi dừng lại vì bất kỳ lỗi nào (`manual-needed:*`, `login/account screen detected`, `captcha`, `verification`, popup kẹt):
  1. **Chụp ảnh hiện trường ngay tại thời điểm phát hiện lỗi (trước khi thoát/dọn dẹp app)**: Phải screencap ngay lúc UI lỗi đang hiển thị để lưu artifact gốc và gửi Farm Alerts qua Telegram (với banner đỏ).
  2. **Giữ nguyên hiện trường trên màn hình máy (không close app ra Home)**: Cho phép user / agent kiểm tra và thao tác cứu hộ trực tiếp trên giao diện lỗi.
  3. **Thời hạn giữ hiện trường & Handoff cleanup**: Máy được giữ nguyên hiện trường lỗi trong suốt thời gian lock còn hiệu lực (tối đa 2 giờ / TTL 7200s). Sau 2 giờ, nếu không có can thiệp thủ công từ user/agent, cơ chế watchdog / lock expire mới thực hiện dọn dẹp (force-stop về Home) và nhả lock để tránh treo máy.
  4. **Cấm chụp alert sau cleanup**: Tuyệt đối không bật cờ dọn dẹp trước khi chụp screencap (`_cleanup_close_all_on_error = True` khi chưa capture), dẫn tới việc alert gửi ảnh màn hình Home gây mất dấu vết nguyên nhân gốc.
