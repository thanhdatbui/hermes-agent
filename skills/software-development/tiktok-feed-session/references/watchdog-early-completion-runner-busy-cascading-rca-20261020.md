# Watchdog Early-Completion & Runner Busy Hold RCA (20/10/2026)

## 1. Hiện Tượng (Symptom)
- Bot Telegram gửi dồn 2 báo cáo nuôi feed liên tiếp cách nhau đúng 5 phút (ví dụ lúc 09:30 gửi Ca 1 - Phiên 1/2, lúc 09:35 gửi Ca 1 - Phiên 2/2).
- Người vận hành thắc mắc vì sao 2 phiên lại trả báo cáo dồn toa thay vì trả đúng giờ kết thúc phiên.

## 2. Truy Vết Dữ Liệu Thực Tế (Timeline Evidence)
- **Ca 1 - Phiên 1/2 (Khung 06:00 – 08:00):**
  - Cụm Kibe: Xong lúc 08:03:14 (sau mốc 08:00).
  - Cụm Admin: Xong lúc 07:51:17 (nhanh hơn mốc 08:00).
- **Ca 1 - Phiên 2/2 (Khung 08:00 – 12:00):**
  - Cụm Kibe & Admin cùng khởi chạy lúc 08:00:10.
  - Cụm Kibe xong lúc 09:22:13.
  - Cụm Admin xong lúc 09:26:32.
  - Sau 09:26: Toàn farm không còn runner nào chạy (`runner_busy == False`).

## 3. Phân Tích Root Cause (Cơ Chế Gây Nghẽn)
1. **Lỗi logic so khớp mốc giờ kết thúc (`_is_session_manifest_completed`):**
   - Trong lúc Phiên 2/2 đang chạy (08:00 – 09:26), `is_feed_runner_active()` luôn là `True`.
   - Để tránh việc một phiên sau làm kẹt phiên trước, watchdog có hàm `is_cluster_session_busy()` kiểm tra xem phiên trước đã xong chưa.
   - Tuy nhiên, `_is_session_manifest_completed()` kiểm tra điều kiện cứng:
     ```python
     if end_hm >= win_end_hm:
         return True
     ```
   - Với Cụm Admin, `win_end_hm = "08:00"`. Admin hoàn tất lúc `07:51` (`07:51 >= 08:00` là `False`).
   - Do đó, `_is_session_manifest_completed` trả về `False` và hàm `is_cluster_session_busy` trả về `True` (bị coi là đang bận), dù lượt chạy sau `row-2-080010` đã bắt đầu.
   - Vì một cụm chưa sẵn sàng (`can_report_all == False`), Phiên 1/2 bị giữ nghẽn toàn bộ cho đến khi Phiên 2/2 kết thúc.
2. **Cơ chế nhả 1 tin / 1 tick (One-message-per-tick):**
   - Khi Phiên 2/2 kết thúc lúc 09:26: Toàn bộ runner rảnh (`runner_busy == False`).
   - Cả Phiên 1/2 và Phiên 2/2 cùng đủ điều kiện gửi báo cáo.
   - Để chống spam, watchdog chỉ gửi 1 phiên mỗi lần quét:
     - Tick 09:30: Gửi Phiên 1/2.
     - Tick 09:35 (5 phút sau): Gửi Phiên 2/2.

## 4. Giải Pháp Kiến Trúc (Architectural Solution)
1. **Truyền cờ `has_later_run` vào kiểm tra manifest:**
   - Trong `is_cluster_session_busy()`: Tính `has_later_run = _has_later_session_run_started(...)` trước.
   - Truyền `has_later_run` vào `_is_session_manifest_completed(..., has_later_run=has_later_run)`.
   - Khi `has_later_run == True`, chỉ cần `end_time` hợp lệ là phiên được xác nhận hoàn tất ngay lập tức (không bắt buộc `end_hm >= win_end_hm`).
2. **Bảo vệ định dạng thời gian (Fail-Closed Timestamp Parsing):**
   - Parse `end_time` sang `end_hm` trước, chuẩn hóa timezone HCMC.
   - Xác thực `re.match(r'^\d{2}:\d{2}$', end_hm)`, bỏ qua các giá trị rác/malformed string (`not-a-date`, `None`, số nguyên).
3. **Đồng bộ song song (Parity Contract):**
   - Luôn cập nhật đồng thời cả 2 bản: `scripts/feed_session_watchdog.py` và `scripts/hermes_cron/feed_session_watchdog.py`.
   - Bổ sung unit test kiểm tra parity giữa 2 file để chống lệch phiên bản.
