# Kỷ Luật Silent Watchdog & Chống Spam Thông Báo Cron

## 1. Cơ Chế Hermes Cron `no_agent: true` & Bẫy Spam
Trong Hermes Cron, các job cấu hình `no_agent: true` vận hành theo quy tắc:
- **`stdout` có dữ liệu (non-empty)**: Hệ thống coi đây là nội dung báo cáo và **gửi nguyên văn (verbatim) vào Telegram**.
- **`stdout` trống (empty / 0 bytes)**: Trạng thái **SILENT** — hệ thống hoàn toàn im lặng, không gửi tin nhắn nào đến người dùng.
- **Exit code != 0 hoặc Timeout**: Hệ thống gửi cảnh báo lỗi thực thi tiến trình.

### Bẫy rò rỉ log gây spam:
- Nhiều script import module phụ trợ (ví dụ: `run_add_2fa_remaining`, GPM API, ADB helpers, Playwright). Các module này thường khởi tạo `logging.basicConfig()` hoặc có các lệnh in `logger.info`, `logger.error` trực tiếp ra `sys.stdout`.
- Khi một dịch vụ bên ngoài gặp lỗi (ví dụ GPM báo `Yêu cầu cập trình duyệt [Chromium] [142]`), log lỗi bị in ra `stdout`.
- **Hậu quả:** Với các cron schedule dày (`*/5 * * * *`), mỗi 5 phút hệ thống lại gửi tin nhắn rác lặp đi lặp lại vào Telegram khiến người dùng bực mình.

---

## 2. Kỷ Luật Triệt Tiêu Rò Rỉ `stdout` (Silent Watchdog Pattern)

Mọi script watchdog chạy định kỳ bắt buộc phải tuân thủ chuẩn bọc bảo vệ:

```python
import sys
import io
import contextlib
import logging

def safe_call_external(func, *args, **kwargs):
    """
    Chặn đứng 100% output rác từ logging và print của thư viện con.
    Không cho phép bất kỳ ký tự nào lọt ra sys.stdout/sys.stderr gốc.
    """
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    
    # Tắt logging tạm thời đối với root logger
    old_level = logging.root.level
    logging.disable(logging.CRITICAL)
    
    try:
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            return func(*args, **kwargs)
    finally:
        logging.disable(logging.NOTSET)
        logging.root.setLevel(old_level)
        sys.stdout = old_stdout
        sys.stderr = old_stderr
```

### Nguyên tắc in kết quả ra `stdout`:
1. **Chỉ in khi có KẾT QUẢ THÀNH CÔNG:**
   ```python
   if success_list:
       print("\n".join(report_lines))
   ```
2. **Nếu thất bại / không có việc / cooldown:**
   - Tuyệt đối KHÔNG in gì ra `stdout`.
   - Ghi log chẩn đoán vào file trạng thái cục bộ (`*.json` hoặc `*.log` trong `runtime/cron-state/`).
   - Kết thúc script với `sys.exit(0)`.

---

## 3. Quy Trình Khẩn Cấp Khi Phát Hiện Spam

Khi nhận tín hiệu người dùng phàn nàn ("đừng có spam thông báo như thế", "sao báo liên tục thế"):

1. **PAUSE NGAY LẬP TỨC (O(1)):**
   - Dùng `cronjob(action='list')` xác định `job_id` của cron vừa gửi tin.
   - Gọi ngay `cronjob(action='pause', job_id='<job_id>')` để chặn đứng tick kế tiếp (tránh bị bắn thêm trong lúc đang debug).
2. **Khóa đích đến (Lockdown Delivery):**
   - Gọi `cronjob(action='update', job_id='<job_id>', deliver='local')`. Chuyển `deliver` về `local` để triệt tiêu mọi khả năng tin nhắn bị lọt ra Telegram/DM.
3. **Sửa code watchdog:**
   - Dispatch Worker bọc context manager triệt tiêu stdout/stderr cho các lệnh gọi hàm con.
   - Test chạy thử focused (`--force --batch-size 1`) và xác nhận stdout hoàn toàn rỗng.
4. **Đồng bộ đa điểm:**
   - Đồng bộ script đã fix trên toàn bộ các vị trí runtime (`AppData/Local/hermes/scripts/`, `Taadaa_Sync_Shared/hermes-cron/scripts/`, `tools/`).
