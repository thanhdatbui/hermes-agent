# Pitfall: Subprocess Output Capture & Concurrency in GPM Watchdogs

## 1. Subprocess Logger Output (Stdout vs Stderr)
- Trong Python, thư viện chuẩn `logging` (ví dụ `logger.info()`, `logger.warning()`, `logger.error()`) mặc định xuất toàn bộ log ra luồng **`sys.stderr`**, chứ KHÔNG ra `sys.stdout`.
- Khi viết script wrapper/watchdog gọi pipeline con (ví dụ `run_oauth_s7_pipeline.py`) qua `subprocess.run(..., capture_output=True)`:
  - Nếu chỉ kiểm tra `"SUCCESS" in proc.stdout`: script sẽ luôn đánh giá là **FAIL** (thất bại giả) vì `proc.stdout` rỗng `""`.
  - **Cách xử lý đúng**:
    ```python
    combined_output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    success = (("SUCCESS" in combined_output and "LAUNCH_FAILED" not in combined_output and "EXCHANGE_FAILED" not in combined_output)
               or "ALREADY_SUCCESS" in combined_output)
    ```

## 2. Concurrency Limit Cho GPM + OAuth
- Khi tự động hóa Playwright Chromium trên GPMLogin kết hợp duyệt ADB trên Samsung S7:
  - Giới hạn cứng: **Tối đa 2 worker song song (`MAX_WORKERS = 2`)**, stagger giữa các worker tối thiểu **5s**.
  - Không được chạy 5-10 workers: việc mở quá nhiều cửa sổ Chromium sẽ gây nghẽn RAM, tranh chấp cổng Sing-box, spam taskbar, xung đột focus ADB và tranh chấp device locks.

## 3. Lọc Ứng Viên GPM Login Đúng Chuẩn
- **Profile Check**: Kiểm tra email đã có profile trong SQLite `profile_data.db` (`SELECT Name FROM profiles`). Nếu chưa có profile trong GPM DB thì bỏ qua để không kích hoạt `PROFILE_NOT_FOUND`.
- **Status Tracker Check**: Đối soát với `oauth_pipeline_status.json`:
  - Bỏ qua tài khoản đã thành công (`omniroute_success`).
  - Bỏ qua tài khoản dính recovery `khoale` (`excluded_khoalee` hoặc recovery email có `khoale`).
  - Bỏ qua tài khoản lỗi mật khẩu / checkpoint (`wrong_password_or_checkpoint`).
  - Bỏ qua tài khoản đang hạ nhiệt IP reCAPTCHA (`ip_cooling_recaptcha`) nếu `retry_after > today`.
  - Với `cooldown_7days`: chỉ nhận khi `retry_after <= today`.
