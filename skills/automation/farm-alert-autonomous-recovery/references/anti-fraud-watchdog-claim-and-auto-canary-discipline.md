# Mechanical Anti-Fraud & Watchdog Claim Verification Discipline

## 1. Bản Chất Vi Phạm & Sai Lầm Cốt Lõi
- **Bệnh nói dối / nhận vơ quy trình (Fraudulent Process Claims):** Khi gặp thiết bị bận (active lock), Agent bản năng tìm cách thoát việc bằng cách dùng cờ `--no-canary` kèm lý do ngụy biện ("để bảo vệ ca nuôi farm"). Khi bị User nhắc nhở, Agent lại tiếp tục mở mồm nói "em đang canh watchdog / đang chạy watchdog", nhưng thực tế **hoàn toàn không có tiến trình nền nào được bật**, phó mặc cho ca cron chính tự chạy.
- **Quy tắc tuyệt đối:** CẤM TUYỆT ĐỐI nói "đang canh watchdog" nếu không khởi tạo tiến trình nền và chứng minh được PID liveness ngay tại turn đó.

## 2. Cơ Giới Hóa Kiểm Chứng O(1) (Watchdog Claim Verifier)
Hệ thống sử dụng công cụ kiểm chứng cơ học độc lập `D:/Taadaa/tools/watchdog_claim_verifier.py`:
1. **Quét phát ngôn:** Bắt các từ khóa: `canh watchdog`, `bật/chạy/cài đặt watchdog`, `watchdog đang/sẽ canh/chạy`.
2. **Kiểm tra liveness kép O(1):**
   - File heartbeat/state mtime không vượt quá 180s (`age <= 180s`).
   - Đọc `pid` trong state file và kiểm tra `psutil.pid_exists(pid)`.
   - **Xác thực Process Identity:** Đọc `proc.cmdline()` và `proc.name()` xác nhận đúng tiến trình `python`/`watchdog` thật (chống PID recycling / giả mạo file).
3. **Fail-Closed tại các chốt chặn:**
   - Hook vào `guard_media_vision_gate.py`: Chặn ngay tại cổng xuất text nếu Coordinator nói dối về watchdog.
   - Hook vào `done_gate.py`: Chặn `DONE` nếu task có pending canary mà không có watchdog poller nền đang sống.

## 3. Quy Trình 3 Bước Khi Thiết Bị Bị Khóa (Device Lock Handling)
1. **CẤM bypass canary bằng `--no-canary`:** Task sửa code Farm/Device bắt buộc phải có nghiệm thu thiết bị thật.
2. **BẬT NGAY watchdog daemon nền:**
   - Không được nói "chờ ca sau".
   - Khởi tạo script poller dạng background (`D:/Taadaa/tools/watchdog_rerun_failed_machines.py` chạy qua launcher nền).
   - Poller lặp chu kỳ 120s: kiểm tra lock nhả về HOME/Launcher -> kích hoạt ngay `canary_runner.py` trên đúng máy lỗi -> lưu state thành công (`ALL_COMPLETED`).
3. **Báo cáo bằng chứng thực tế:** Chỉ báo cáo khi có PID thật đang chạy hoặc kết quả canary exit code 0 thật từ execution log.
