# Fast Swipe Interaction Boost & Smart Watchdog Reporting (2026-08-26)

## 1. Fast Swipe Interaction Rate Compensation
- **Vấn đề:** Khi kích hoạt cơ chế Fast Swipe (2–4 video lướt nhanh mù 2–5s không dump XML $\rightarrow$ 1 video Deep Inspect dump XML), các video lướt nhanh không thể nhận diện nút Thích/Follow trên UI. Nếu giữ nguyên tỉ lệ tương tác thông thường per-video (8% like, 5% follow), tổng tương tác cả phiên sẽ bị loãng xuống rất thấp.
- **Giải pháp bù trừ tại nhịp Deep Inspect (có dump XML):**
  - `DEFAULT_DEEP_LIKE_RATE_PERCENT = 40` (nâng từ 20% lên 40%). Cứ mỗi lần dừng đọc XML, xác suất bấm Thả tim là 40%.
  - `DEFAULT_DEEP_FOLLOW_RATE_PERCENT = 20` (bổ sung mới 20% organic follow tại nhịp Deep Inspect).
- **Quy tắc giới hạn Fast Swipe theo Tab (Tab-scoped Fast Swipe):**
  - **Chỉ áp dụng Fast Swipe cho tab Đề xuất (`FEED_TYPE_FOR_YOU`):** Chiếm ~85% thời lượng nuôi feed.
  - **Tab Đang theo dõi (`FEED_TYPE_FOLLOWING`) & Bạn bè (`FEED_TYPE_FRIENDS`):** **TUYỆT ĐỐI KHÔNG FAST SWIPE**. Bắt buộc 100% video ở 2 tab này phải thực hiện Deep Inspect (dump XML) để đọc UI và thả tim theo tỉ lệ ưu tiên của tab (15% Following, 25% Friends).

## 2. Loại Bỏ Cửa Sổ Cứng 90 Phút ở Runner
- **Vấn đề:** Runner cũ lọc `slot <= now <= slot + 90 phút`. Khi cron picker bị trễ hoặc chạy đầu ngày, hơn nửa số máy có slot sớm bị tính là "quá hạn 90 phút" và bị bỏ qua, dẫn đến việc chỉ có một phần số máy được dispatch.
- **Giải pháp:** Bỏ điều kiện lọc 90 phút cứng trong `_due_entries`. Khi đến ca của Row nào, gom toàn bộ danh sách máy có nick trong Row đó giao cho 40 workers điều phối cuốn chiếu (với stagger khởi động ngẫu nhiên), đảm bảo 100% máy đều được chạy.

## 3. Smart Watchdog Reporting (Chốt Báo Cáo Theo Tiến Trình Thật)
- **Vấn đề:** Watchdog cũ chốt báo cáo cứng theo mốc đồng hồ (07:30 là chốt Phiên 1), dẫn đến báo cáo cắt ngọn thiếu máy khi các máy đang chạy dở.
- **Giải pháp:**
  1. Watchdog tự động đọc tổng số máy dự kiến (`expected_count`) của Row từ cấu hình nguồn.
  2. Chỉ chốt gửi báo cáo khi:
     - Toàn bộ máy dự kiến trong ca đã hoàn thành (`completed_count >= expected_count`).
     - HOẶC đã hết khung giờ phiên VÀ không còn tiến trình runner/feed nào đang chạy dở (`now_hm >= end and not is_feed_runner_active()`).
  3. Báo cáo hiển thị rõ định dạng: `Tổng máy xử lý: <completed> / <expected> máy`.
