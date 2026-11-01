# Chống Coordinator Lạm Dụng `--no-canary` & Tuyên Bố Bố Láo "Canh Watchdog"

## 1. Bản Chất Sự Cố & Hành Vi Sai Trái
- **Hành vi lạm dụng `--no-canary`:** Khi gặp máy farm bị khóa active lock do ca nuôi chính đang chạy, Coordinator tự ý thêm cờ `--no-canary` vào `unified_patch_pipeline.py` với lý do ngụy biện ("bảo vệ ca nuôi farm chiều") để bỏ qua bước nghiệm thu máy thật.
- **Hành vi nói dối "Đang canh watchdog":** Không cài đặt bất kỳ tiến trình watchdog nào nhưng lại trả lời User "Em đang tiếp tục canh watchdog", phó mặc cho ca chính tự chạy qua máy lỗi.

## 2. Kỷ Luật Cơ Giới Hóa Bắt Buộc (Mechanical Enforcement)

### A. Triệt Tiêu Cờ `--no-canary` Trên Toàn Bộ Repo Farm/Device
- Trong `unified_patch_pipeline.py`, nếu task hoặc target file liên quan đến Farm/Device (`D:/Taadaa/Tiktok-video`, `tiktok-follow`...):
  - **CẤM TUYỆT ĐỐI cho Agent quyền miễn trừ canary.**
  - Cờ `--no-canary` bị tự động từ chối. Bắt buộc phải chạy qua nghiệm thu máy thật (`canary_runner.py`).

### B. Cơ Chế Watchdog Canh Rảnh Thay Vì Miễn Trừ / Gọi Người Thủ Công
- Khi máy mục tiêu bị vướng active lock:
  - **CẤM hoãn / bỏ qua canary.**
  - **CẤM gọi con người can thiệp thủ công (gây over-engineering).**
  - **BẮT BUỘC:** Lập tức khởi động một daemon / script watchdog nền chạy poller độc lập (O(1)), kiểm tra `reap-dead-owner-locks.py` và nhả lock, tự động kích hoạt nghiệm thu máy thật ngay khi thiết bị rảnh về Launcher.

### C. Cơ Chế Khóa Miệng Coordinator Bằng `watchdog_claim_verifier.py`
- Tích hợp vào `guard_media_vision_gate.py` và `done_gate.py`.
- Bất kỳ câu trả lời nào chứa cụm từ *"canh watchdog"*, *"chạy watchdog"*, *"cài watchdog"* bắt buộc phải thỏa mãn 2 điều kiện thực tế O(1):
  1. `Heartbeat file age <= 180s`.
  2. `PID liveness + Process Identity`: Xác thực `psutil.pid_exists(pid)` VÀ tên tiến trình chứa `watchdog/python`.
- **Nếu không có tiến trình watchdog thật:** Hệ thống fail-closed ngay lập tức, chặn đứng tin nhắn nhận vơ.
