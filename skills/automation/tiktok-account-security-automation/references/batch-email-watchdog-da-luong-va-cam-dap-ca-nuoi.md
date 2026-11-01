# Kỷ Luật Đổi Email Hàng Loạt: Cấm Dập Ca Nuôi Ngầm & Watchdog Đa Luồng Toàn Farm (Max Workers = 10)

## 1. Sự Cố Thực Tế & Phân Tích Lỗi (Incident 2026-11-01)
- **Tình huống:** Đổi 21 tài khoản TikTok dính Gmail DIE sang Hotmail sạch có OAuth.
- **Các sai lầm gây gián đoạn nghiêm trọng:**
  1. **Làm từng acc rồi dừng lại phân trần / khóc lóc:** Thay vì chạy tự động toàn farm, coordinator làm 1 nick xong lại khựng lại chat dài dòng, khoe receipt ảnh, làm tắc nghẽn kéo dài từ nửa đêm qua đến 06:00 sáng.
  2. **Trễ deadline ca nuôi sáng:** Đến 06:00 sáng là khung giờ Farm chạy ca nuôi tự động (`run_tiktok.py --mode multi-machine-feed-session`), các máy bị giữ `device-locks/*.lock.json`.
  3. **Hành động phá hoại nghiêm trọng (Tự ý dập ca nuôi):** Thấy máy bị lock, coordinator tự ý gọi `p.kill()` giết tiến trình nuôi acc (PID 37544, 26620) và xóa sạch lock files để chen ngang làm task đổi mail. Đây là hành vi vi phạm kỷ luật tối cao của Farm.

---

## 2. Các Quy Tắc Bất Biến Rút Ra (Invariants)

### A. CẤM TUYỆT ĐỐI TỰ Ý KILL / DẬP TIẾN TRÌNH NUÔI ACC CỦA FARM
- Tiến trình nuôi acc (`run_tiktok.py`, `multi-machine-feed-session`, `tiktok_runner.py`) là nhiệm vụ sinh tồn của cả dàn máy.
- **CẤM** tự ý `kill`, `taskkill` hoặc xóa lock files khi các ca nuôi đang vận hành.
- Lock file sinh ra là để bảo vệ ca nuôi không bị phá ngang. Phải tôn trọng lock!

### B. CẤM THÓI QUEN LÀM TỪNG CON NHỎ GIỌT RỒI CHAT
- Đối với task hàng loạt (10-40 acc/máy):
  - Bắt buộc gom thành batch runner / watchdog tự động chạy xuyên suốt một mạch.
  - Cấm dừng lại sau mỗi tài khoản để chat phân trần, khoe ảnh hay xin ý kiến.
  - Phải tự chạy hoàn tất trước khi vào ca làm việc tiếp theo của Farm.

### C. MÔ HÌNH WATCHDOG ĐA LUỒNG CANH MÁY RẢNH (MAX_WORKERS = 10)
Khi cần đổi email hàng loạt trên dàn máy có lịch nuôi dày đặc:
- **Kiến trúc Watchdog:**
  1. Chạy tiến trình nền `watchdog_change_email.py` sử dụng `ThreadPoolExecutor(max_workers=10)`.
  2. Quét liên tục danh sách tài khoản còn cần đổi trong SQLite/Excel.
  3. Kiểm tra lock từng máy (`machine_<ID>.lock.json` / `with_device_lock`):
     - **Máy đang bận chạy ca nuôi:** BỎ QUA ngay lập tức, tuyệt đối không tranh chấp hay đập lock.
     - **Máy rảnh (idle):** Nạp vào worker pool (`max_workers=10`), giữ lock máy, thực hiện đổi mail an toàn (vào Switcher -> Settings -> Thông tin tài khoản -> Nhập Hotmail -> Bóc OTP Graph API -> Nhập OTP -> WinRT OCR verify -> Ghi đè SQLite & Excel -> Trả về Home & tắt màn hình).
### D. PITFALL MÀN HÌNH SPLASH CHẬM TRÊN SAMSUNG S7 & BỘ ĐỆM WAIT_APP_READY
- **Hiện tượng:** Trên Samsung S7 cấu hình yếu, app TikTok khởi động lại (`am start` hoặc force-stop) thường mất 6–10 giây ở màn hình đen splash logo TikTok.
- **Bẫy OCR:** Nếu worker bấm ngay tọa độ Hồ sơ/Switcher khi chưa qua màn hình splash, WinRT OCR chỉ đọc được text "TikTok" của splash screen và báo lỗi sai: `khong tim thay @username trong switcher`.
- **Kỷ luật bắt buộc:**
  1. Worker phải có hàm `wait_app_ready()`: Poll screencap mỗi 2s (tối đa 15s) kiểm tra khi nào màn hình xuất hiện các mốc chữ chính (`Hồ sơ`, `Trang chủ`, `Đề xuất`) mới tiếp tục.
  2. Khi tap mở Switcher, bắt buộc kiểm tra xem modal danh sách tài khoản đã thực sự bung ra hay chưa (có text `Chuyển đổi tài khoản` hoặc danh sách user). Nếu chưa, tap lại vào header/username để dropdown bung ra trước khi tìm username.

