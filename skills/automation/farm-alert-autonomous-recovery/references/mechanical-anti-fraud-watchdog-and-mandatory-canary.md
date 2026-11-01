# Mechanical Anti-Fraud Watchdog & Mandatory Canary Enforcement

## 1. Nguyên Tắc Cốt Lõi (Invariants)
- **CẤM TUYỆT ĐỐI tự ý dùng `--no-canary`:** Agent khi sửa bất kỳ script nào liên quan đến Farm/Device (repo `Tiktok-video`, `tiktok-luot nuoi acc`, `tiktok-follow`...) tuyệt đối không được tự ý miễn trừ canary.
- **Kỷ Luật Khi Thiết Bị Bận (Device Busy / Active Lock):**
  - Không được dùng cớ "máy đang bận ca nuôi" để bỏ qua canary hoặc thụ động chờ ca sau.
  - **BẮT BUỘC khởi tạo ngay Watchdog Daemon nền (Background Poller O(1)):** Canh thiết bị nhả lock về Home/Launcher để tự động kéo máy ra chạy nghiệm thu canary thực tế.
  - CẤM gọi con người (User) can thiệp thủ công vào luồng canary khi máy lock, tránh over-engineering và phá vỡ tính tự động hóa.
- **CẤM BỐ LÁO NHẬN VƠ "ĐANG CANH WATCHDOG":**
  - Mọi tuyên bố "canh watchdog / đã bật watchdog" bắt buộc phải đi kèm bằng chứng cơ học kiểm chứng được:
    1. Tiến trình background daemon có PID thực tế đang sống (`psutil.pid_exists(pid)`).
    2. File state/heartbeat được cập nhật trong vòng `<= 180s`.
  - Không có tiến trình PID sống mà mở mồm nói "đang canh" bị coi là hành vi gian dối nghiêm trọng nhất (Watchdog Claim Fraud) và bị gate chặn đứng lập tức.

## 2. Kiến Trúc Cơ Giới Hóa O(1) Đã Triển Khai
1. **Gate Chặn Khước Từ `--no-canary` (`unified_patch_pipeline.py`):**
   - Tự động phát hiện task sửa repo Farm/Device, bỏ qua cờ `--no-canary` do Agent truyền và ép buộc luồng nghiệm thu máy thật.
2. **Watchdog Daemon Rerun Pattern (`watchdog_rerun_failed_machines.py` + `run_watchdog_rerun_daemon.py`):**
   - Poller lặp chu kỳ 120s kiểm tra lock thiết bị qua `admin_ssh.py` / local `.lock.json`.
   - Máy nhả lock -> tự động gọi `canary_runner.py` / `admin_canary_wrapper.py` chạy preflight & upload verify.
   - Hoàn tất -> tự cập nhật `state.json` và kết thúc daemon (`ALL_COMPLETED`).
3. **Cổng Thẩm Định Chống Khai Man (`watchdog_claim_verifier.py`):**
   - Hook vào `guard_media_vision_gate.py` và `done_gate.py`.
   - Quét regex các claim watchdog trong output text của Coordinator.
   - Đối soát O(1) timestamp `< 180s` và kiểm tra PID liveness; vi phạm -> fail-closed ngay lập tức.
