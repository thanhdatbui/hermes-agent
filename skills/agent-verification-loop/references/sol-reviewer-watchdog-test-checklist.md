# Sol Reviewer Score Gate Checklist for Watchdog & Automation Suites (>= 85 pts)

Khi bổ sung test hoặc audit cho watchdog/automation runner (ví dụ `post_noon_chain_watchdog.py`) nhằm đạt điểm review cao từ Sol Reviewer:

1. **Lock Cleanup on Exception:**
   - Chứng minh khối `finally` luôn bảo đảm xóa file lock (`running_lock.unlink()`) ngay cả khi tác vụ con gặp exception (`subprocess.CalledProcessError`, `RuntimeError`, `KeyboardInterrupt`).
   - Mocking pattern: Patch một hàm phase (như `run_gmail_batch` hoặc `run_tiktok_2fa_batch`) raise Exception và assert `running_lock.exists() is False` sau khi gọi watchdog `main()`.

2. **Lock Timeout & Stale Detection:**
   - Kiểm tra rành mạch 2 nhánh thời gian:
     - Stale lock (`mtime > TIMEOUT`, e.g. > 5400s): Watchdog ghi đè hoặc bỏ qua lock cũ và tiếp tục chạy.
     - Active lock (`mtime < TIMEOUT`, e.g. < 5400s): Watchdog phát hiện có tiến trình đang chạy và thoát an toàn (`return 0`).
   - Mocking pattern: Patch `Path.stat` hoặc tạo file lock thật với `os.utime` lùi mtime.

3. **Telemetry & Error Classification Parsing:**
   - Parser output phải có unit test bao phủ các định dạng output khác nhau (Key-Value `TOTAL=... SUCCESS=...`, Regex `Machine X: OK/FAIL`, Markdown table fallback).
   - Tách bạch rõ các loại lỗi script (lỗi nghiệp vụ vs lỗi infra/timeout/crash) để telemetry report luôn chính xác và không bị gộp chung.

4. **Runner CLI Contract Compatibility:**
   - Unit test kiểm tra câu lệnh command line (arguments, flags như `--live`, `--max-workers N`, `PYTHONPATH`) phải khớp 100% với argument parser của script mục tiêu.
