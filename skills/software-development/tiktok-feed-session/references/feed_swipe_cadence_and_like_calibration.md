# Feed Swipe Cadence & Tab Like Calibration (2026-09-18)

## 1. Cơ chế Lướt Fast Swipe & Deep Inspect xen kẽ
- **Tab Đề xuất (For You - 70% thời lượng session):**
  - Fast Swipe mạnh: Lướt nhanh 2.0s - 5.0s ngẫu nhiên từ 2 đến 4 video rồi mới Deep Inspect 1 video (dump XML).
  - Tỉ lệ tim tại Deep Inspect: 40% -> Sau khi bù trừ các video lướt nhanh ra tỉ lệ tim thực tế: **8% - 12%** tổng video For You.
  - Tác dụng: Nhẹ máy, giảm tải 70% CPU cho toàn farm 70-100 máy, giữ trust người dùng giải trí thông thường.

- **Tab Bạn bè (Friends - 15% thời lượng session):**
  - Môi trường tab: 100% là video bạn bè nội bộ 2 chiều của farm (không có người lạ/quảng cáo).
  - Fast Swipe nhẹ xen kẽ: Lướt qua 1 video ngắn (làm Noise tự nhiên) rồi Deep Inspect 1-2 video.
  - Tỉ lệ tim tại Deep Inspect: **65%** -> Sau bù trừ thực tế: **45% - 55%** tổng video Bạn bè.
  - Tác dụng: Đẩy tim và retention tự nhiên cho video của dàn nick farm đăng, tránh biến thành máy dập tim 100% lộ pattern.

- **Tab Đang theo dõi (Following - 15% thời lượng session):**
  - Fast Swipe nhẹ xen kẽ (1 fast - 1 deep).
  - Tỉ lệ tim tại Deep Inspect: **35%** -> Sau bù trừ thực tế: **25% - 30%** tổng video Following.

## 2. Báo cáo Cron Watchdog (`feed_session_watchdog.py`)
Báo cáo Telegram hoàn tất từng phiên bắt buộc hiển thị rõ tỉ lệ tim tổng hợp và bóc tách từng tab để kiểm soát đối chiếu:
```text
  + Thả tim: 185 tim / 1480 video (12.5%) [Đề xuất: 110 (9.8%) | Bạn bè: 45 (48.4%) | Following: 30 (27.3%)]
```

## 3. Quản trị Deadman Switch / Progress Supervisor
- Hook `guard_progress_supervisor.py` giám sát loop agent cần phân biệt rõ Coordinator vs Worker:
  - Coordinator cần thời gian đọc log, phân tích chuyên sâu, tham vấn Sol/Claude.
  - Trần timeout an toàn: `MAX_STALL_SECONDS >= 3600` (60m) và `MAX_ACTION_COUNT >= 100`.
  - Nhận diện `delegate_task` và các thao tác điều phối là State Change hợp lệ, tránh đóng băng nhầm phiên làm việc.
