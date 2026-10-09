# Feed Watchdog Midnight Rollover & Cascading Shift Delay (2026-09-06)

## 1. Triệu chứng sự cố
- Người dùng nhận báo cáo Telegram: `[TIKTOK NUÔI ACC] Ca 3 - Phiên 3/3 (Tối - Đăng video) hoàn tất (Row 5) • Tổng máy xử lý: 2 máy` và phản ánh: *"Ủa sao tổng máy xử lý 2 máy clgt"*.
- Toàn farm thực tế có 73 máy đang chạy, nhưng báo cáo chỉ ghi nhận đúng 2 máy.

---

## 2. Phân tích nguyên nhân gốc (Root Cause Analysis)

### A. Lỗi logic "Chốt non" khi qua ngày (Midnight Date Rollover)
1. **Chuyển ngày lúc 00:00:**
   - Phiên Ca 3 Phiên 3 ngày `2026-09-05` khởi chạy lúc `22:32:50` trên 73 máy.
   - Do chạy đầy đủ cả lướt feed lẫn upload video, tiến trình kéo dài vắt qua nửa đêm.
   - Khi đồng hồ điểm `2026-09-06 00:00:33`, cron watchdog `feed_session_watchdog.py` kích hoạt.
   - Tại thời điểm này: `today = "2026-09-06"`, trong khi `target_date = "2026-09-05"`. Do đó cờ `is_today = (target_date == today)` trở thành `False`.
2. **`can_report_session` return `True` vô điều kiện:**
   - Code cũ:
     ```python
     def can_report_session(
         is_today: bool,
         completed_expected_count: int,
         expected_count: int,
         now_hm: str,
         window_end_hm: str,
         runner_busy: bool,
     ) -> bool:
         if is_today:
             return (completed_expected_count >= expected_count and not runner_busy) or (now_hm >= window_end_hm)
         return True
     ```
   - Khi `is_today == False`, hàm lập tức trả về `True` mà không kiểm tra xem runner có đang bận (`runner_busy`) hay không.
3. **Lệch chuỗi nhận diện tiến trình runner trong `is_feed_runner_active`:**
   - Hàm `is_feed_runner_active()` kiểm tra `"multi_machine_feed_session" in cmd` (dấu gạch dưới).
   - Nhưng lệnh runner thực tế sinh ra là `--mode multi-machine-feed-session` (dấu gạch nối) qua `run_tiktok.py`.
   - Dẫn đến `is_feed_runner_active()` trả về `False` ngay cả khi tiến trình runner đang hoạt động.
4. **Hậu quả:**
   - Lúc 00:00:33, mới chỉ có M55 (23:58:05) và M13 (23:58:39) ghi xong `summary.txt`.
   - Watchdog thấy `can_report_session -> True` vội vàng chốt báo cáo 2 máy, gửi lên Telegram và ghi nhận phiên đã xong vào `feed_session_reported.json`.
   - 71 máy còn lại hoàn thành từ 00:01 đến 00:22 bị bỏ sót hoàn toàn.

---

### B. Nguyên nhân Cascading Delay khiến phiên cuối vắt qua nửa đêm
1. **Phiên 2 bị nghẽn do máy lỗi:**
   - Lịch dự kiến: Phiên 2 chạy 20:25 - 21:25.
   - Thực tế chạy lúc 20:31:23. Một số máy dính lỗi ADB/mạng/ATX timeout phải chờ thu hồi lock, khiến Phiên 2 kéo dài tới tận `22:31:43` mới nhả lock hoàn toàn.
2. **Phiên 3 bị dồn khởi động muộn:**
   - Không thể chạy lúc 22:10 như lịch dự kiến. Phải đợi đến cữ cron tiếp theo lúc `22:32:50` mới khởi động.
3. **Phiên 3 mang tải nặng nhất:**
   - Phiên 3 cuối ca gộp 3 tác vụ: Lướt Feed + Follow chéo + Upload video (render/download video, ADB push, thao tác UI đăng bài, verify Published Grid profile).
   - 73 máy chia 2 đợt (max workers 40) tiêu tốn 50 phút $\rightarrow$ kết thúc lúc `00:22:49` rạng sáng hôm sau.

---

## 3. Quy chuẩn khắc phục & Invariant bắt buộc

### Quy tắc Watchdog an toàn qua nửa đêm:
1. **Khóa cứng kiểm tra `runner_busy`:**
   - Nếu `runner_busy == True`, TUYỆT ĐỐI KHÔNG được chốt báo cáo, bất kể là phiên trong ngày hay phiên ngày hôm trước vắt qua đêm.
2. **Nhận diện đầy đủ các biến thể tiến trình:**
   - `is_feed_runner_active` phải kiểm tra cả:
     - `"multi-machine-feed-session"` (hyphen)
     - `"multi_machine_feed_session"` (underscore)
     - `"run_tiktok.py"`
     - `"hermes_cron_runner.py"`
     - `"tiktok_runner.py"`
3. **Điều kiện chốt cho ngày hôm trước (`not is_today`):**
   - Chỉ chốt khi `not runner_busy` VÀ (đã đạt đủ expected machines HOẶC thời gian hiện tại đã qua cữ an toàn sau ca 3, ví dụ sau 02:00 sáng).
4. **Quy trình phục hồi khi bị chốt non:**
   - Chờ tiến trình runner kết thúc hoàn toàn (`PID` exit).
   - Xóa key session bị lỗi (vd `2026-09-05_ca3_phien3`) trong `D:\Taadaa\runtime\kibe\cron-state\feed_session_reported.json`.
   - Watchdog ở lần chạy kế tiếp sẽ tự động gom đủ 73 máy và phát lại báo cáo chuẩn xác.
