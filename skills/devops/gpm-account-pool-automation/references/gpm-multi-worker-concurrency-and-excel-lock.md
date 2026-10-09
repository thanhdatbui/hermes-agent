# Concurrency Safety: Multi-Threaded GPM Operations & Excel Data Integrity

## 1. Vấn đề cốt lõi (Race Conditions on Shared Storage)
Khi chạy automation đa luồng trên GPM (`ThreadPoolExecutor`, `max_workers >= 5`):
1. **Excel Data Corruption (`openpyxl` non-thread-safe):**
   - Định dạng file `.xlsx` thực chất là một kho lưu trữ ZIP nén các file XML cấu trúc (`xl/workbook.xml`, `xl/worksheets/sheet1.xml`, ...).
   - Khi nhiều luồng (ví dụ 30 luồng) cùng gọi:
     ```python
     wb = openpyxl.load_workbook(EXCEL_PATH)
     # edit cells...
     wb.save(EXCEL_PATH)
     ```
   - Hai hoặc nhiều tiến trình ghi đồng thời vào file `.xlsx` sẽ làm hỏng ZIP header hoặc làm cắt ngang luồng XML đang ghi dở.
   - Hậu quả:
     - `Bad magic number for file header` (hỏng ZIP header, `zipfile.BadZipFile`).
     - `not well-formed (invalid token): line 1, column N` (`xml.etree.ElementTree.ParseError`).

2. **Cron Scheduler Output Leakage (Telegram Spam):**
   - Các script watchdog hoặc module con thường import thư viện có sẵn `logging.basicConfig(...)` với `logging.StreamHandler(sys.stdout)`.
   - Trên Hermes Cron hoặc bất kỳ background runner nào có cơ chế `no_agent: true`: Mọi ký tự xuất hiện trên `sys.stdout` đều được coi là message gửi về Telegram/Discord.
   - Khi chạy 30 luồng, hàng trăm dòng log `[INFO]`, `[ERROR]`, `[WARNING]` tuồn thẳng ra stdout tạo ra cơn bão spam tin nhắn.

---

## 2. Giải pháp kỹ thuật chuẩn mực

### A. Khóa Lock đồng bộ cho thao tác ghi Excel
Mọi hàm lưu dữ liệu vào Master Excel (`master_gmail_manager.xlsx`) và Clean Excel (`gmail_clean_v2.xlsx`) BẮT BUỘC phải dùng khóa luồng `threading.Lock()` (hoặc file lock nếu chạy đa process):

```python
import threading
import openpyxl

EXCEL_LOCK = threading.Lock()

def sync_secret_to_excels_safe(email: str, secret_key: str) -> bool:
    with EXCEL_LOCK:
        # Load, cập nhật và save an toàn tuyệt đối
        wb = openpyxl.load_workbook(EXCEL_PATH)
        ws = wb.active
        # ... cập nhật dữ liệu ...
        wb.save(EXCEL_PATH)
        wb.close()
    return True
```

### B. Bịt kín `stdout` trong Watchdog (`no_agent: true`)
1. **Gỡ bỏ `StreamHandler(sys.stdout)` trong log con:**
   - Chỉ giữ `logging.FileHandler(LOG_FILE, encoding="utf-8")`.
   - Nếu cần in terminal debug khi chạy tay, cấu hình `StreamHandler(sys.stderr)` thay vì `sys.stdout`.
2. **Bọc cách ly `stdout`/`stderr` khi gọi module ngoài:**
   ```python
   import io
   import contextlib
   import logging

   # Tạm thời chặn stdout của thư viện bên thứ 3 hoặc module import
   f_out = io.StringIO()
   f_err = io.StringIO()
   with contextlib.redirect_stdout(f_out), contextlib.redirect_stderr(f_err):
       # Hạ log level hoặc gọi hàm GPM
       res = setup_authenticator_for_profile(profile_info)
   ```
3. **Chỉ print duy nhất 1 block tổng kết khi kết thúc ca:**
   - Chỉ `print("\n".join(report_lines))` ở hàm `main()` sau khi toàn bộ workers đã hoàn thành (`as_completed`).
   - Nếu không có action thành công hoặc máy rảnh: script kết thúc im lặng hoàn toàn (`0 bytes stdout`).
