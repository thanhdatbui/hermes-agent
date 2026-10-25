# Quy Chuẩn Phân Định Báo Cáo Watchdog: Feed Session vs Follow Session

## 1. Nguyên Tắc Cốt Lõi (Non-Negotiable)
Tuyệt đối không lẫn lộn nghiệp vụ và chỉ số giữa 2 luồng báo cáo:
- **Nuôi Feed** không có khái niệm "nhả follow", "thành công follow".
- **Follow Chéo** không quan tâm đến "tổng swipe video", "thả tim", "đọc comment".

---

## 2. Báo Cáo Lướt Nuôi Acc (`feed_session_watchdog.py`)
- **Mục tiêu:** Giám sát **Flow thiết kế** của ca nuôi (xem các máy có phân bổ đúng và đều vào các Row trong Pool của Ca hay không, có bị dồn cục vào 1 Row hay không).
- **Vị trí hiển thị:** Ngay bên dưới dòng `+ Fail` trong khối `• Lướt Feed:`.
- **Định dạng chuẩn:**
  ```text
  🏢 【FARM KIBE - MÁY 1-80】 (Run: row-0-140735)
  • Tổng máy xử lý: 80 máy
  • Lướt Feed:
    + Success (48): M15, M16, ...
    + Fail (32): M18, ...
    + Phân bổ Row (49 máy): Row 4 (1 máy | 2.0%) | Row 7 (1 máy | 2.0%) | Row 8 (47 máy | 95.9%)
    + Trống slot/chưa có nick (0): Không có
    + Thả tim: 82 tim / 883 video (9.3%) [Đề xuất: 82 (100.0%) | Bạn bè: 0 | Following: 0]
    + Follow tự nhiên: 5 lượt / 883 video (0.6%) [Đề xuất: 5 | Bạn bè: 0]
    + Đọc comment: 12 lượt / 883 video (1.4%)
  ```
- **Cơ chế thu thập:** Trích xuất trường `account_row` từ `run_manifest.json` của từng máy trong `parse_run_all`, sau đó tổng hợp `row_counts` và tính phần trăm trên tổng số máy chạy.

---

## 3. Báo Cáo Follow Chéo (`follow_session_watchdog.py`)
- **Mục tiêu:** Đo lường **Sức khỏe & Tỷ lệ nhả follow** của dàn nick khi đi follow trên từng dải IP/Proxy.
- **Thống kê theo cơ chế sức khỏe đàn nick:**
  - `💪 Nhóm Khỏe (10+ lượt)`: Nick cứng, trust cao, follow mượt.
  - `🌱 Hồi phục 2 (5 - 9 lượt)`: Nick đang dưỡng tăng trưởng.
  - `🌱 Hồi phục 1 (1 - 4 lượt)`: Nick mới hồi phục hoặc thử thách.
  - `Nhả follow`:
    - `- Nhả liền (0 lượt)`: Vừa bấm follow hoặc vuốt là bị nhả ngay.
    - `- Nhả ở Hồi phục 1 / 2 / Cấp Khỏe`: Bị nhả sau khi đã tích lũy một số lượt follow.
  - `Bỏ qua`:
    - `Cooldown nhả follow (48h)`: Nick dính nhả đang trong thời gian cách ly follow.
    - `Chưa đủ điều kiện`: Dưới 6-10 video, dưới 21 ngày tuổi...
- **Cầu dao tự ngắt IP (IP Circuit Breaker):** Kích hoạt khi phát hiện proxy có máy dính nhả để khóa cứu các máy cùng proxy.
