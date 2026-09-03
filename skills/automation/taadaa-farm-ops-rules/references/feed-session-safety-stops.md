# Feed Session Safety Stops & Verification Markers

## 1. Cơ Chế Dừng Khẩn Cấp (Safety Stop)
- Khi script `multi-machine-feed-session` hoặc `feed-session-smoke` phát hiện `verification marker detected` (qua phân tích cây UI XML hoặc popup verification như captcha kéo hình, khớp ảnh, yêu cầu mã OTP/xác thực danh tính):
  - Kích hoạt cơ chế cách ly an toàn tài khoản: ngăn chặn tap mù có thể dẫn tới khóa acc.
  - Tự động đóng app TikTok (`am force-stop`) và đưa thiết bị về màn hình Home Android (`input keyevent HOME`).
  - Gắn nhãn đỏ/vàng trên báo cáo alert gửi về Telegram Farm Alerts kèm ảnh chụp trạng thái máy lúc đã về Home.

## 2. Cách Xem Lại Màn Hình Lỗi Thực Tế
- Ảnh đính kèm alert trên Telegram là ảnh máy ở màn hình Home sau khi app đã được đóng an toàn.
- Muốn xem lại captcha/màn hình xác minh thực tế:
  - Mở lại app TikTok trên thiết bị tương ứng (bằng tay hoặc ADB).
  - Hoặc tra cứu UI XML / log sự kiện ngay trước thời điểm dừng phiên trong thư mục `.ai-runs/` hoặc artifact run.
