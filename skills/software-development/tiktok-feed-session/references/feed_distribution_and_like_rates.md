# Cấu Hình Phân Bổ Tab Và Tỉ Lệ Thả Tim Nuôi Acc (User duyệt 2026-09-08)

## 1. Phân bổ lượt xem các tab (`DEFAULT_FEED_DISTRIBUTION`)
* **Đề xuất (`for-you`): 70%** (0.70)
  - Giữ tỷ lệ chủ đạo để tài khoản học interest graph như người dùng thật.
  - Ngăn TikTok gắn cờ cụm máy bot farm chỉ xem chéo nội bộ.
* **Bạn bè (`friends`): 15%** (0.15)
  - Tăng từ mức cũ (7%) lên 15% để mỗi phiên 12-15 video ghé xem ~2 video bạn bè.
  - Kích hoạt thuật toán đề xuất video chéo nội bộ giữa các dàn máy.
* **Đang follow (`following`): 15%** (0.15)
  - Ghé xem video của creator/kênh đã follow.

## 2. Tỉ lệ thả tim (`DEFAULT_FEED_LIKE_RATES`)
* **Bạn bè (`friends`): 70%** (cũ: 25%)
  - Tim đẩy tương tác nội bộ rất mạnh mẽ.
  - Vẫn giữ 30% video không tim để tạo độ nhiễu tự nhiên (organic noise).
* **Đang follow (`following`): 30%** (cũ: 15%)
  - Tỷ lệ vừa phải vì list following có cả kênh/creator bên ngoài được follow khi lướt For You.
* **Đề xuất (`for-you`): 8%**
  - Nhịp Deep Inspect bù Fast Swipe áp dụng `deep_like_rate_percent = 40%`.

## 3. Quy tắc kỹ thuật trong code (`feed_swipe_smoke.py`)
* Tab **Friends** và **Following** là 100% Deep Inspect (không áp dụng Fast Swipe).
* Cơ chế bù like của Fast Swipe (`fast_swipe["deep_like_rate_percent"]`) chỉ áp dụng khi `current_feed_type == for-you`.
* Khi đang ở tab `friends` hoặc `following`, bắt buộc ăn theo đúng tỷ lệ danh nghĩa riêng (`like_rates.get(current_feed_type)`), không bị Fast Swipe For You ghi đè thành 40%.
