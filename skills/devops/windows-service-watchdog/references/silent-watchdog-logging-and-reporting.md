# Silent Watchdog Logging Standard for Cronjobs (no_agent=True)

## 1. Nguyên lý hoạt động của Hermes Scheduler với `no_agent=True`
- Hermes scheduler chạy script watchdog định kỳ qua `sys.executable` hoặc bash.
- **Quy tắc chuyển phát (Delivery Semantics):**
  - Khi `stdout` **CÓ nội dung** (dù chỉ là 1 dòng log INFO hay 1 ký tự): scheduler đóng gói toàn bộ `stdout` và tự động gửi tới channel đích (Telegram Farm Alert).
  - Khi `stdout` **HOÀN TOÀN RỖNG**: scheduler im lặng (**SILENT**), không gửi tin nhắn nào.
  - Khi script kết thúc với non-zero exit code / unhandled exception: scheduler tự động gửi alert báo lỗi.

---

## 2. Pitfall phổ biến: Logger ghi ra `sys.stdout` mặc định
Nhiều script cấu hình Python `logging` với `StreamHandler(sys.stdout)` để xem log console khi chạy thủ công:
```python
# SAI - Gây spam Telegram mỗi chu kỳ cron (15 phút/lần) dù không có việc gì:
fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
sh = logging.StreamHandler(sys.stdout)
logger.addHandler(fh)
logger.addHandler(sh)
```
Hậu quả: Mỗi chu kỳ cron, các dòng log thông thường (`[INFO] Bắt đầu đồng bộ...`, `[INFO] Không có thay đổi.`) in ra `sys.stdout`, khiến Hermes scheduler hiểu nhầm là có báo cáo cần gửi và bắn tin nhắn rác vào Telegram.

---

## 3. Kiến trúc chuẩn cho Watchdog Script

### 3.1. Phân tách Logging: FileHandler mặc định, StreamHandler qua CLI Flag `--verbose`
- Mặc định: Chỉ gắn `FileHandler` để lưu trữ nhật ký chi tiết vào đĩa (`logs/*.log`) phục vụ truy vết/debug O(1).
- Chỉ gắn `StreamHandler(sys.stdout)` khi có cờ `--verbose` hoặc `-v`.

```python
import argparse
import logging
import sys

logger = logging.getLogger("watchdog_name")
logger.setLevel(logging.INFO)

# 1. Luôn ghi log chi tiết vào file
fh = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
fh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
logger.addHandler(fh)

def main():
    parser = argparse.ArgumentParser(description="Watchdog Description")
    parser.add_argument("-v", "--verbose", action="store_true", help="In chi tiết log ra stdout")
    args = parser.parse_args()

    # Chỉ bật console stream khi chạy thủ công kiểm tra
    if args.verbose:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
        logger.addHandler(sh)
```

### 3.2. Quy tắc in Báo cáo Tổng kết ra `stdout`
- Khi trạng thái **bình thường / không có hành động thực tế**:
  - Không gọi bất kỳ lệnh `print()` nào.
  - `stdout` rỗng $\rightarrow$ Cronjob hoàn toàn im lặng.
- Khi **CÓ hành động can thiệp thực tế** (ví dụ: tạo mới profile, gỡ tài khoản, auto-heal):
  - In đúng **1 dòng báo cáo sạch** hoặc block tóm tắt cô đọng qua `print(...)`.
  - Tuyệt đối không để log trung gian lẫn vào thông điệp người dùng.

```python
    # Thực hiện tác vụ
    created_count = do_create_profiles()
    cleaned_count = do_cleanup_accounts()

    # Chỉ báo cáo khi có thay đổi thực tế
    if created_count > 0 or cleaned_count > 0:
        parts = []
        if created_count > 0:
            parts.append(f"Tạo mới {created_count} profile LIVE")
        if cleaned_count > 0:
            parts.append(f"Đã dọn {cleaned_count} tài khoản DIE")
        print(f"[WATCHDOG] {' | '.join(parts)}")
```

---

## 4. Checklist nghiệm thu Watchdog Script
1. Chạy mặc định không tham số: `python script.py` $\rightarrow$ Exit code 0, không có bất kỳ ký tự nào in ra stdout (`len(stdout.strip()) == 0`).
2. Chạy với cờ verbose: `python script.py -v` $\rightarrow$ Các dòng log INFO/DEBUG hiển thị đầy đủ trên màn hình.
3. Log file trên đĩa vẫn ghi nhận đầy đủ timestamps và dữ liệu mỗi chu kỳ chạy.
