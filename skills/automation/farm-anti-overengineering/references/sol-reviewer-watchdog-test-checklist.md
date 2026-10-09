# Sol Reviewer Score Requirement Checklist: Watchdog & Automation Scripts (>= 85 pts)

Khi viết test hoặc refactor các watchdog/runner tự động hóa (`post_noon_chain_watchdog.py`, `watchdog_*.py`) để đạt điểm review cao từ Sol Reviewer (>= 85 điểm):

1. **Lock Cleanup on Exception (Bảo đảm giải phóng lock khi văng lỗi):**
   - Phải có unit test chứng minh khi subprocess hoặc tác vụ chính ném lỗi bất ngờ (Exception/KeyboardInterrupt), khối `finally` vẫn luôn unlink/dọn dẹp file lock (`running.lock`).
   - Mock test: ném Exception trong mock function của phase con, assert `lock_file.exists() is False`.

2. **Lock Timeout / Stale Lock Handling (Xử lý lock quá hạn vs lock đang chạy):**
   - Test 2 nhánh rõ ràng:
     - Lock stale (`mtime > TIMEOUT`): Watchdog phải log cảnh báo/bỏ qua lock cũ và tiếp tục thực thi.
     - Lock active (`mtime < TIMEOUT`): Watchdog phải phát hiện tiến trình khác đang chạy và thoát an toàn (`return 0`).
   - Mock test bằng `os.path.getmtime` hoặc mock file stat với timestamp lùi về quá khứ.

3. **Telemetry & Granular Reporting (Phân loại chi tiết metrics):**
   - Đảm bảo test bao phủ đầy đủ các hàm parser output (`parse_summary_counts`) qua nhiều định dạng (Key-value `TOTAL=... SUCCESS=...`, Regex đếm từng máy, Markdown table fallback).
   - Tách biệt rõ ràng các loại lỗi script (lỗi nghiệp vụ vs lỗi hạ tầng/timeout/crash) để telemetry không bị gộp chung.

4. **Runner CLI Contract Compatibility:**
   - Unit test kiểm tra câu lệnh shell / subprocess command line được sinh ra phải tương thích 100% với argument parser của script mục tiêu (ví dụ `--live`, `--max-workers N`, paths).
