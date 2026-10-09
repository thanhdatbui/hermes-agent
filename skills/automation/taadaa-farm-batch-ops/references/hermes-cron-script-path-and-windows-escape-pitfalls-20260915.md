# Hermes Cron Script Path Resolution, Windows Escape Pitfalls & Pre-flight Run Verification (15/09/2026)

## 1. Hiện Tượng & Sự Cố Thực Tế
- Người vận hành nhận cảnh báo lỗi Telegram từ Hermes Cron Scheduler:
  ```text
  Cronjob Response: post-evening-account-reconcile-watchdog (job_id: 1d3035a5fde2)
  ⚠️ Cron 'post-evening-account-reconcile-watchdog' failed: Script not found: C:\Users\Kibe\AppData\Local\hermes\scripts\watchdog_post_evening_reconcile.py
  ```
- Phản ứng gay gắt từ người vận hành: *"Địt cụ mày phá gì thế"*.

## 2. Phân Tích Nguyên Nhân Cốt Lõi (Root Causes)

### A. Nhầm Lẫn Đường Dẫn Scripts Runtime Của Hermes Trên Windows
- Hermes Cron Scheduler trên Windows quy ước đường dẫn tương đối của tham số `script: "<name>.py"` BẮT BUỘC nằm tại:
  `C:\Users\Kibe\AppData\Local\hermes\scripts\` (tức `~/AppData/Local/hermes/scripts/`).
- Subagent / Coordinator nhầm lẫn với quy ước Linux (`~/.hermes/scripts/`), tạo script tại `C:\Users\Kibe\.hermes\scripts\watchdog_post_evening_reconcile.py`.
- Khi đến lịch chạy (20:20), Scheduler quét thư mục AppData/Local thì không tìm thấy file, lập tức phát sinh lỗi `Script not found`.

### B. Bẫy Escape Ký Tự Điều Khiển Trong Chuỗi Python Trên Windows (`\r`, `\t`, `\a`)
- Khi viết script Python tạo file tự động qua template string (hoặc nhúng vào terminal `python -c "content = ..."`):
  - `\runtime` bị escape `\r` (carriage return) $\rightarrow$ biến thành `untime` (ví dụ `D:\Taadaauntime`).
  - `\tools` bị escape `\t` (tab character) $\rightarrow$ đường dẫn chứa ký tự tab vô hình làm gãy path.
  - `\automation` bị escape `\a` (ASCII Bell `\x07`) $\rightarrow$ đường dẫn biến thành `\x07utomation`.
- Hậu quả: Ngay cả khi file tồn tại, script khi thực thi sẽ văng lỗi `FileNotFoundError: [Errno 2] No such file or directory: 'D:\\Taadaauntime\\...'`.

### C. Quên Kiểm Chứng Trực Tiếp (`cronjob action='run'`) Trước Khi Bàn Giao
- Sau khi dùng tool `cronjob(action='create')`, agent không thực thi test probe một lần mà để nguyên lịch hẹn chờ nổ ngầm.
- Đến khi cron kích hoạt vào ban đêm thì bắn lỗi thẳng vào chat Telegram của người dùng.

## 3. Quy Chuẩn Vận Hành & Khắc Phục Bắt Buộc

### 1. Đồng Bộ Script 3 Vị Trí (Local Runtime + Git Deploy + OneDrive Sync)
Mọi script chạy bởi Hermes Cron trên host Kibe/Admin BẮT BUỘC phải được ghi hoặc copy đồng bộ vào cả 3 nơi:
```bash
# 1. Local Runtime của Hermes Scheduler
C:\Users\Kibe\AppData\Local\hermes\scripts\<script_name>.py

# 2. Thư mục Git Deploy chuẩn
D:\Taadaa\Hermes\deploy\hermes-home\scripts\<script_name>.py

# 3. Thư mục OneDrive Shared Sync
D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\<script_name>.py
```

### 2. Quy Tắc Forward-Slash Tuyệt Đối Trong Code Python
Trong toàn bộ mã nguồn script và template tạo file, TUYỆT ĐỐI CẤM dùng backslash `\` trần trong chuỗi đường dẫn. BẮT BUỘC dùng forward-slash `/`:
```python
# ĐÚNG (Chuẩn cross-platform, không bao giờ bị escape \r, \t, \a):
STATE_FILE = Path("D:/Taadaa/runtime/kibe/cron-state/post_evening_reconcile_state.json")
CLEANER_SCRIPT = Path("D:/Taadaa/tools/clean_and_reconcile_farm_accounts.py")
PYTHON_EXE = Path("D:/Taadaa/python-envs/automation/Scripts/python.exe")

# SAI (Nguy hiểm chết người):
STATE_FILE = Path(r"D:\Taadaa\runtime\kibe\cron-state\...")  # Dễ bị biến dạng \r -> carriage return
```

### 3. Quy Trình 3 Bước Nghiệm Thu Khi Tạo/Sửa Cron Job
Bất kỳ khi nào tạo mới (`action='create'`) hoặc sửa đổi (`action='update'`) một cron job:
1. **Kiểm tra file vật lý:** Dùng `Test-Path` hoặc `read_file` xác nhận file tồn tại tại `C:\Users\Kibe\AppData\Local\hermes\scripts\<script>.py`.
2. **Kiểm tra cú pháp & chạy thử độc lập:** Chạy trực tiếp qua terminal `python "C:/Users/Kibe/AppData/Local/hermes/scripts/<script>.py"` xem có lỗi cú pháp / import hay không.
3. **Kích hoạt test qua Scheduler:** BẮT BUỘC gọi `cronjob(action='run', job_id='<job_id>')` ngay lập tức để xác nhận `last_status == 'ok'` và `execution_success == true`.
