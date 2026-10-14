# Quy Hoạch Farm 3 Ca Nuôi, Cửa Sổ Rảnh Đêm 21:30-04:00 & Chu Kỳ Báo Cáo Định Kỳ 6H (15/10/2026)

## 1. Bối Cảnh & Xoá Bỏ Ca 4 (Đêm) Khỏi Lịch Nuôi
- **Thực tế vận hành:** Farm Taadaa đã chính thức **bỏ hoàn toàn Ca 4 nuôi acc TikTok ban đêm** (trước đây chạy 00:00 và 01:30).
- **Lịch nuôi acc hiện tại chuẩn hóa 3 Ca x 2 Phiên / ngày:**
  - **Ca 1 (Sáng):** Phiên 1 lúc `06:00`, Phiên 2 lúc `08:00` (+ Hook Upload/Follow). Xong toàn bộ trước `09:30`.
  - **Ca 2 (Trưa):** Phiên 1 lúc `12:00`, Phiên 2 lúc `14:00` (+ Hook Upload/Follow). Xong toàn bộ trước `15:30`.
  - **Ca 3 (Tối):** Phiên 1 lúc `18:00`, Phiên 2 lúc `20:00` (+ Hook Upload/Follow). Xong toàn bộ trước `21:30`.
  - **Dọn cache cuối ngày:** `04:00 -> 04:45` sáng (`end-of-day-clear-tiktok-cache`).
- **Khoảng rảnh rỗi vàng của Farm (> 10 tiếng/ngày):**
  - **Đêm dài (6.5 tiếng liên tục):** `21:30 → 04:00` sáng hôm sau.
  - **Sáng giữa ca:** `09:30 → 11:45`.
  - **Chiều giữa ca:** `15:30 → 17:45`.

## 2. Hai Tàn Dư Kiến Trúc Cũ Cần Triệt Tiêu (Root Cause Analysis)

### Tàn dư 1: Bẫy "Chết lâm sàng" vì chờ Ca 4 (`is_ca4_finished`)
- Trong `cron_night_tiktok_2fa_watchdog.py`: Kiểm tra `if not is_ca4_finished(today_str): return 0`.
- Do Ca 4 không còn tồn tại, `feed_session_reported.json` không bao giờ có key `ca4_phien2` -> Watchdog 2FA đêm bị chặn 100%, chưa từng chạy được một lần nào.
- **Khắc phục:** Xoá bỏ vĩnh viễn kiểm tra `is_ca4_finished`. Kiểm tra cửa sổ an toàn qua `is_safe_rolling_window(now)` kết hợp `is_feed_runner_active() == False`.

### Tàn dư 2: Bẫy ngắt ca tĩnh lúc 23:45 & Gán nhãn ảo "Nhường lịch nuôi"
- Trong `post_evening_avatar_watchdog.py`: Hàm `is_after_evening_window` ngắt ca khi `h == 23 and m > 45`, xuất báo cáo tổng kết và dừng chạy suốt đêm.
- Đồng thời dòng code:
  ```python
  if tot_miss > 0 and not all_done:
      session_lines.append(f"• Bỏ qua an toàn: {tot_miss} máy (nhường lịch nuôi TikTok / lock tiến trình khác)")
  ```
  đã tự động gán nhãn cho toàn bộ `tot_miss` (số lượt acc còn thiếu) thành "nhường lịch nuôi".
- Thực tế: Lúc 23:50 không hề có ca nuôi TikTok nào; `tot_miss = 40` là số lượt slot Tik còn thiếu trên 13 máy vật lý (phần lớn là máy offline M10, M30, M255 hoặc kẹt Switcher M213, M264), không có máy nào thực sự "nhường lịch nuôi".
- **Khắc phục:**
  - Cho phép chạy cuốn chiếu xuyên đêm `21:30 → 04:00` thay vì dừng lúc 23:45.
  - Phân biệt rõ số slot acc còn thiếu (`tot_miss`) vs số máy vật lý độc lập (`len(distinct_machines)`).
  - Không gán nhãn "nhường lịch nuôi" cho máy lỗi hoặc máy đang trong hàng đợi cuốn chiếu.

## 3. Kiến Trúc Cuốn Chiếu An Toàn & Chu Kỳ Báo Cáo Định Kỳ 6H

### Nguyên tắc cuốn chiếu né lịch nuôi:
1. **Guard Giờ Nuôi (Cận giờ 15-20 phút):**
   - Né Ca 1: `05:45 → 09:30`
   - Né Ca 2: `11:45 → 15:30`
   - Né Ca 3: `17:45 → 21:30`
   - Né Dọn cache: `04:00 → 04:45`
2. **Kiểm tra tiến trình & Lock:**
   - Nếu `is_feed_runner_active()` hoặc `is_feed_active()` == True -> Skip.
   - Kiểm tra `device-locks`: Tác vụ nào đụng máy đang có lock `status in ('running', 'active')` thì né riêng máy đó ra, không dừng cả batch.

### Chu kỳ Báo cáo Định kỳ Mỗi 6H (00:00, 06:00, 12:00, 18:00):
- **Tại sao chọn mốc 6h:** Trùng khớp với các mốc giao ca của Farm (06:00 bắt đầu ca sáng, 12:00 bắt đầu ca trưa, 18:00 bắt đầu ca tối, 00:00 giữa ca đêm).
- **Cơ chế im lặng ngoài mốc:** Trong các lần chạy thăm dò giữa giờ (mỗi 5-15 phút), script chạy ngầm im lặng, cập nhật DB/state, không gửi Telegram để chống spam.
- **Điều kiện xuất báo cáo Telegram:**
  1. Khi chạm mốc 6h (`now.hour in (0, 6, 12, 18) and now.minute < 30`) và chưa báo cho window key `YYYY-MM-DD_HH`.
  2. HOẶC khi toàn farm đạt **100% hoàn tất** (`all_clusters_done`), gửi 1 tin nghiệm thu duy nhất rồi im lặng.
