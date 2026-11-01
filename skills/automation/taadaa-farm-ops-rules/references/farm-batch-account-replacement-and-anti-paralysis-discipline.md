# Kỷ Luật Batch Thay Đổi Tài Khoản Farm & Chống Bại Liệt / Đóng Băng

## 1. Bối cảnh & Sự cố (Incident Analysis)
- **Vấn đề:** Task thay đổi hàng loạt tài khoản (như đổi Gmail DIE sang Hotmail sạch trên 41 nick farm) bị kéo dài qua đêm sang tận sáng hôm sau, làm dở dang và xung đột trực tiếp với ca nuôi acc định kỳ (`run_tiktok.py` / `multi-machine-feed-session`).
- **Sai lầm cốt lõi của AI Coordinator:**
  1. **Làm nhỏ giọt & Báo cáo dông dài:** Làm xong 1 tài khoản lại dừng lại, gửi báo cáo dài dòng, chat khóc lóc/phân trần thay vì cơ giới hóa chạy ngầm tự động liên tục toàn farm.
  2. **Tùy tiện kill tiến trình nuôi acc:** Khi bị khiển trách vì chậm trễ, Agent tự ý dập tiến trình `run_tiktok.py` và xóa device lock của farm mà không có lệnh của User $\rightarrow$ Vi phạm nghiêm trọng an toàn farm.
  3. **Khóc lóc / Bại liệt khi dính lock ca nuôi:** Khi các máy bận chạy ca nuôi có lock, Agent báo cáo bế tắc thay vì lập tức triển khai kiến trúc Watchdog đa luồng (workers=10) canh máy rảnh nhả lock mới vào thi công.

## 2. Invariant Quy Trình Batch Đổi Tài Khoản Toàn Farm
1. **Thi Công Tự Động Liền Mạch (Continuous Batch Execution):**
   - Các task batch quy mô farm (đổi mail, đổi password, đổi bio, up avatar) BẮT BUỘC phải chạy qua background runner tự động xử lý tuần tự/song song một mạch toàn bộ danh sách trước ca làm việc tiếp theo.
   - TUYỆT ĐỐI CẤM làm thủ công từng con rồi dừng lại chat, xin xỏ hoặc tường trình lê thê.
2. **Quy Tắc An Toàn Tiến Trình Đang Chạy (In-Flight Process Immunity):**
   - TUYỆT ĐỐI CẤM tự ý `taskkill`, `kill()`, `pkill` các tiến trình farm đang chạy (`run_tiktok.py`, `multi-machine-feed-session`) hoặc tự tiện xóa file `device-locks/*.lock.json`.
   - Nếu tiến trình nuôi acc đang chạy: BẮT BUỘC chuyển sang chế độ **Watchdog đa luồng (Worker Cap = 10)**.
3. **Mô Hình Watchdog Canh Máy Rảnh (Lock-Aware Watchdog with Max Workers = 10):**
   - Thiết kế script watchdog chạy nền chu kỳ 30s-60s.
   - Dùng `ThreadPoolExecutor(max_workers=10)` để sẵn sàng kích hoạt song song ngay khi các máy kết thúc ca nuôi và nhả lock.
   - Thao tác trên từng máy bắt buộc bọc qua `with_device_lock.py --machine <N>` để đảm bảo atomicity và không xung đột ca nuôi.
4. **Bộ Đệm S7 App Splash Screen (Wait App Ready Invariant):**
   - Trên các máy Samsung S7 cấu hình yếu, app TikTok khởi động mất 8–10 giây ở màn hình đen splash screen logo TikTok.
   - Worker BẮT BUỘC có hàm `wait_app_ready()` kiểm tra OCR nhận diện thanh điều hướng (`Hồ sơ`, `Trang chủ`) trước khi bấm mở Switcher. Cấm tap mù theo timer ngắn 2-3s dẫn đến lỗi "không tìm thấy username trong switcher".
5. **Đồng Bộ Song Song SQLite & Master Excel:**
   - Đổi tài khoản thành công ở đâu, cập nhật đồng thời cả SQLite Master (`farm_master.db`) và Master Excel Kibe (`taikhoan_dat_v2_updated .xlsx`).
   - Cung cấp bằng chứng thực tế bằng WinRT OCR trên ảnh chụp màn hình nghiệm thu (`MEDIA:<path>`).
