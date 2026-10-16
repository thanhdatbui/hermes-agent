# Watchdog Sys.Path Cron Fallback, Architecture Gate Line Budget, and Multi-Channel Report Invariants (2026-10-16)

## 1. Sự Cố Triệt Tiêu: Spam Alert Report và Cron Import Failure

### Triệu Chứng
Mỗi 5 phút, Cron Scheduler gửi thông báo lỗi đỏ liên tục vào các topic Telegram:
```text
Cronjob Response: tiktok-follow-session-watchdog (job_id: 6991768931e1)
⚠️ Cron 'tiktok-follow-session-watchdog' failed: Script exited with code 1
stderr:
Traceback (most recent call last):
  File ".../scripts/feed_session_watchdog.py", line 22, in <module>
    from watchdog.lock import ProcessLock, is_feed_runner_active, is_pid_alive
ModuleNotFoundError: No module named 'watchdog'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File ".../scripts/follow_session_watchdog.py", line 14, in <module>
    import feed_session_watchdog as fsw
  File ".../scripts/feed_session_watchdog.py", line 35, in <module>
    from scripts.watchdog.lock import ProcessLock, is_feed_runner_active, is_pid_alive
ModuleNotFoundError: No module named 'scripts.watchdog'
```

Đồng thời, khi có lỗi Follow chéo >= 8 máy, báo cáo của **Lướt Feed** (gửi về topic tiktok-luot nuoi acc) bị biến dạng thành:
`🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT HÀNG LOẠT (X máy lỗi script Follow) - Ca N (Row M)`
gây hiểu lầm rằng toàn bộ luồng nuôi acc bị dừng, vi phạm phân định độc lập 3 kênh.

---

## 2. Nguyên Nhân Kỹ Thuật Gốc Rễ (Root Cause Analysis)

1. **Cơ chế nạp sys.path[0] của Python khi chạy Cron Script:**
   - Trong cron scheduler, hàm `_run_job_script` thực thi script qua `subprocess.run([sys.executable, str(script_path)], cwd=job_workdir, ...)`.
   - Theo chuẩn Python runtime, khi chạy `python path/to/script.py`, Python luôn luôn gán `sys.path[0]` bằng thư mục chứa script (`path/to`), tức thư mục runtime staging.
   - `job_workdir` (cwd) KHÔNG tự động được đưa vào `sys.path`.
   - Script đồng bộ `cron_sync_watchdog.py` chỉ đồng bộ các file `.py` phẳng, KHÔNG sao chép các thư mục package con như `watchdog/`.
   - Hậu quả: Script runtime hoàn toàn không thể import `from watchdog.lock ...` hay `from scripts.watchdog.lock ...`.

2. **Bẫy Sửa Mò workdir của Agent Trước:**
   - Agent trước thấy lỗi `ModuleNotFoundError`, tưởng nhầm là do thiếu workdir nên gọi cập nhật workdir trong cấu hình cron.
   - Việc này hoàn toàn vô hiệu vì Python không tìm package trong cwd nếu script được gọi qua đường dẫn file cụ thể ngoài thư mục đó.

3. **Bẫy Đồng Bộ Kép (Dual-Copy Parity) & Architecture Line Budget:**
   - `python_runner/tests/test_follow_session_watchdog.py` có test case `test_feed_session_watchdog_and_hermes_cron_sync` yêu cầu `scripts/feed_session_watchdog.py` và `scripts/hermes_cron/feed_session_watchdog.py` phải giống nhau byte-for-byte.
   - `tests/test_watchdog_architecture_gate.py` có test case `test_feed_session_watchdog_line_budget` yêu cầu `len(lines) <= 1450` trần cứng. File hiện tại đang ở 1.444 dòng. Bất kỳ lần vá nào thêm > 6 dòng mà không dọn bớt dòng trống sẽ làm sập architecture gate ngay lập tức.

---

## 3. Quy Tắc Khắc Phục Chuẩn (Standard Resolution Pattern)

### A. Tự Động Bơm sys.path Tối Giản Trước Khối Import
Tại đầu file `feed_session_watchdog.py` và `follow_session_watchdog.py`:
```python
from zoneinfo import ZoneInfo

# Fallback: if running outside repo root (e.g. cron staging dir), ensure repo scripts dir is in sys.path
for _p in (r"D:\Taadaa\tiktok-luot nuoi acc\scripts", r"D:\Taadaa\tiktok-luot nuoi acc", os.getcwd()):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from watchdog.lock import ProcessLock, is_feed_runner_active, is_pid_alive
```
Lưu ý: Khi thêm đoạn code này, phải xóa bớt các dòng trống liên tiếp ở các vị trí khác trong file để giữ tổng số dòng <= 1.447 dòng, bảo đảm không chạm trần 1.450 dòng của Architecture Gate.

### B. Đồng Bộ Hóa Song Song Sang Thư Mục hermes_cron/
Sau khi sửa `scripts/feed_session_watchdog.py` và `scripts/follow_session_watchdog.py`:
BẮT BUỘC copy đè sang `scripts/hermes_cron/`:
```bash
cp "D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py" "D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron/feed_session_watchdog.py"
cp "D:/Taadaa/tiktok-luot nuoi acc/scripts/follow_session_watchdog.py" "D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron/follow_session_watchdog.py"
```

### C. Triệt Tiêu Lỗi Kéo Theo Giữa 3 Kênh Báo Cáo (Channel Isolation)
- Nhóm **Lướt Feed** (-5377611430): CHỈ báo cáo tiến độ feed và chỉ cảnh báo đỏ khi bản thân Feed bị lỗi hàng loạt. CẤM gộp `tot_fl_err` (Follow) hay `tot_up_err` (Upload) vào header `🚨 [FARM ALERT]` của kênh Feed.
- Nhóm **Follow chéo** (-5127276494): Script `follow_session_watchdog.py` chịu trách nhiệm độc quyền tính toán `tot_fl` và gửi alert/báo cáo về kênh Follow.
- Nhóm **Đăng Video** (-5435853713): `dispatch_split_reports` chỉ bắn nhánh `up_p` vào -5435853713.

### D. Đồng Bộ Ngay Lập Tức Sang Runtime Cron
Sau khi commit trong repo:
1. Sao chép 2 file sang repo deploy `deploy/hermes-home/scripts/`.
2. Chạy `python D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_sync_watchdog.py`.
3. Kiểm tra kết quả `[CRON-SYNC] Hoàn tất đồng bộ: scripts_synced=4`.
4. Gọi cron run chạy thử cả 2 job để chứng thực `last_status == 'ok'` (exit code 0).
