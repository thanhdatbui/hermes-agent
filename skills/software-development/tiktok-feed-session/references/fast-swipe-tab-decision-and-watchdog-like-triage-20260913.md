# Case Triage: Fast Swipe nuốt đếm chuyển Tab & Chuẩn hóa Báo cáo Watchdog (2026-09-13)

## 1. Triệu chứng
- Runner lướt hoàn tất đủ 16–22 video mỗi máy nhưng 100% video đều nằm ở tab Đề xuất (`for-you`).
- Tab Bạn bè (`friends`) và Đang Follow (`following`) có lượt xem = 0 và like = 0, dù cấu hình cài đặt phân phối: `Đề xuất 70% (like 8%) | Bạn bè 15% (like 70%) | Following 15% (like 30%)`.
- Báo cáo Telegram báo `Fail (61)` máy nhưng thực tế có tới 45 máy chỉ đơn thuần là trống nick ở Row 7 (`account row 7 is empty (no username), skipping`), gây hiểu nhầm toàn farm lỗi.
- Báo cáo thiếu thống kê tổng số tim và tỷ lệ like theo từng tab.

## 2. Root Cause
1. **Bug nuốt lượt đếm ở nhánh Fast Swipe (`feed_swipe_smoke.py`)**:
   - Biến đếm nhịp chuyển tab `videos_until_tab_decision = random.randint(3, 8)` chỉ được trừ ở nhánh Deep Inspect: `videos_until_tab_decision -= 1`.
   - Nhánh `fast_swipe` (chiếm 15/21 video mỗi máy) gọi `continue` mà **quên trừ `videos_until_tab_decision -= 1`**.
   - Dẫn đến biến đếm không bao giờ giảm về `<= 0` để gọi `_weighted_feed_choice`. Toàn bộ 80 máy kẹt 100% ở tab Đề xuất từ đầu đến cuối phiên.
2. **Watchdog gom nhóm chưa chuẩn (`feed_session_watchdog.py`)**:
   - Mọi máy `!= success` đều bị đưa vào mảng `fail`, bao gồm cả máy trống nick (`batch-config-error` / `is empty (no username)`).
   - Template tin nhắn Telegram chưa bóc tách trường `like_counts` từ `summary.txt`.

## 3. Quy chuẩn khắc phục
1. **Trong `feed_swipe_smoke.py`**:
   - Luôn bổ sung `videos_until_tab_decision -= 1` trước mọi lệnh `continue` trong vòng lặp swipe (kể cả nhánh Fast Swipe).
2. **Trong `feed_session_watchdog.py`**:
   - Trích xuất `like_counts` và `total_swipes_completed` từ per-machine `summary.txt`.
   - Tách riêng danh sách máy `Trống slot/chưa có nick` (các máy không nằm trong danh sách cấu hình của Row đó hoặc có lý do trống slot).
   - Đưa dòng thống kê chi tiết vào báo cáo Telegram:
     `+ Thả tim: X tim / Y video (Z%) [Đề xuất: A | Bạn bè: B | Following: C]`
