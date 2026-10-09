# Case Study & Quy Chuẩn Kỹ Thuật: Pre-Session Scrape T0 & Idle Scrolls Mode 2 (2026-09-27)

## 1. Hiện Tượng Lệch Dương Ảo Khi Đối Soát Following Sau Phiên (Reconciliation Drift)
- **Triệu chứng:**
  Báo cáo tổng kết Phiên 2 (cuối buổi sáng) ghi nhận lệch dương ảo trên nhiều tài khoản:
  `M45 (@hang.bui813): script báo 1 | web tăng +4 (Lệch +3)`
- **Điều tra thực tế từ SQLite & XML app:**
  1. Lúc 07:03 sáng, cron cào toàn farm ghi nhận `@hang.bui813` có 190 following.
  2. Lúc 08:19 sáng (ngay trước khi Phiên 2 chạy), giao diện app đã hiển thị 193 following (+1 follow tự nhiên lúc lướt feed Phiên 1 + 2 follow cũ TikTok flush cache).
  3. Trong Phiên 2, script follow thêm đúng 1 nick `@anhdo829` (+1), nâng tổng lên 194.
  4. Sau Phiên 2, watchdog cào web đạt 194. Do không có snapshot sát giờ chạy Phiên 2, watchdog lùi về tìm snapshot trước `session_start_iso` (08:00) và lấy nhầm mốc 07:03 (190):
     $$\Delta_{\text{web}} = 194 - 190 = +4$$
     So với báo cáo script là 1, watchdog báo lệch ảo +3.

## 2. Giải Pháp Chuẩn Hóa: Pre-Session Scrape T0 Trong `tiktok_runner.py`
- Ngay trong `_spawn_feed_session()`, trước khi khởi tạo `run-feed-session.ps1`:
  - Trích xuất toàn bộ `tik_id` thuộc Row sắp chạy từ `taikhoan_run_safe.xlsx`.
  - Gọi subprocess chạy `tiktok_account_tracker.py` cào snapshot baseline $T_0$ sát giờ mở phiên (timeout 60s, bọc fail-safe).
- Khi phiên kết thúc, watchdog cào $T_1$ và đối soát:
  $$\Delta = T_1 - T_0$$
  Phép trừ lấy đúng biến động của riêng phiên đó, triệt tiêu 100% lệch dương ảo.

## 3. Nút Thắt Cuộn Sâu Mode 2 Trong Following List Của Anchor
- **Vấn đề:**
  Trong Mode 2 (Anchor Following), nếu trong danh sách của Anchor xuất hiện nhiều tài khoản người ngoài liên tiếp trước khi đến nhóm nick farm nội bộ (`internal_uids`), runner có biến đếm `idle_scrolls`.
  Mức trần cũ `idle_scrolls >= 5` khiến runner dừng sớm và kết thúc với lý do `đã follow sẵn (skip)` dù bên dưới vẫn còn nick farm chưa khai thác.
- **Quy chuẩn:**
  Nâng ngưỡng `idle_scrolls` từ **5 lên 15 lần cuộn** trong `mode2_follow_followers.py` kết hợp safe-skip anchor bị lỗi mở tab sang anchor tiếp theo, đảm bảo quét triệt để danh sách trước khi kết thúc ca.
