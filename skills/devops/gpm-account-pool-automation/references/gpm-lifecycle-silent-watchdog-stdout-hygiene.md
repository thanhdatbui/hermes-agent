# GPM & S7 Lifecycle Silent Watchdog: Phòng Chống Rò Rỉ Log Ra Stdout (Farm Alert)

## 1. Bản Chất Kiến Trúc `no_agent: true` của Hermes Cron
- Với các cron job cấu hình `no_agent: true` (ví dụ `gpm-lifecycle-sync-watchdog`, job ID: `b0f7828c992e`):
  + **Stdout rỗng (`len == 0`)** $\rightarrow$ Hệ thống xem như không có gì cần báo, **im lặng hoàn toàn** (Silent Watchdog).
  + **Stdout có ký tự bất kỳ** $\rightarrow$ Hermes bốc nguyên văn stdout gửi thẳng về kênh đích (`deliver: telegram:-5373649734` - Farm Alert).
- Do đó, nếu có bất kỳ dòng log `[INFO]`, log kết nối ADB (`AdbClient initialized...`), log quét máy... lọt vào `sys.stdout`, Telegram Farm Alert sẽ bị nã tin debug liên tục mỗi 15 phút.

## 2. Nguyên Nhân Gốc Rễ Gây Rò Rỉ Log
1. **Module-level `logging.basicConfig`**:
   Script thư viện con (ví dụ `preflight_s7_rolling_cleanup.py`) đặt `logging.basicConfig(handlers=[StreamHandler(sys.stdout)])` ngay ở phạm vi module (ngoài hàm).
2. **Hiệu ứng ô nhiễm Root Logger khi `import`**:
   Khi script chính (`sync_gpm_lifecycle.py`) gọi `from preflight_s7_rolling_cleanup import remove_account_adb`:
   - `logging.basicConfig` được thực thi và gán `StreamHandler(sys.stdout)` vào **Root Logger**.
   - Mọi logger khác trong tiến trình (bao gồm `automation_core.adb`, `requests`, `urllib3`, và các module con) mặc định có `propagate = True` đều chuyển tiếp log lên Root Logger $\rightarrow$ phun thẳng ra `sys.stdout`.

## 3. Quy Tắc Bất Biến Cho Helper / Thư Viện Farm
1. **Tuyệt đối cấm `logging.basicConfig(handlers=[StreamHandler(sys.stdout)])` ở module level**:
   - Mọi script helper phải cấu hình handler riêng vào file log hoặc dùng `NullHandler`.
   - Đặt `logger.propagate = False` để không lan truyền lên root.
   ```python
   # Chuẩn an toàn cho helper module:
   LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
   os.makedirs(LOG_DIR, exist_ok=True)
   logger = logging.getLogger("S7RollingCleanup")
   logger.setLevel(logging.INFO)
   logger.propagate = False
   if not logger.handlers:
       _fh = logging.FileHandler(os.path.join(LOG_DIR, "preflight_s7_rolling_cleanup.log"), encoding="utf-8")
       _fh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
       logger.addHandler(_fh)
   ```
2. **Nếu script có chế độ chạy CLI trực tiếp (`main`)**:
   - Chỉ thêm `StreamHandler` vào `sys.stderr`, KHÔNG đưa vào `sys.stdout`.
   ```python
   if __name__ == "__main__":
       sh = logging.StreamHandler(sys.stderr)
       sh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
       logger.addHandler(sh)
       main()
   ```

## 4. Cơ Chế Tự Vệ Chủ Động Trong Script Watchdog
Trước khi thực thi logic nghiệp vụ hoặc import các thư viện bên thứ ba, script watchdog bắt buộc phải tẩy sạch `sys.stdout` khỏi root logger:
```python
# Tẩy sạch mọi handler trỏ vào stdout trên root logger
root_logger = logging.getLogger()
for h in list(root_logger.handlers):
    if isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) in (sys.stdout, sys.__stdout__):
        root_logger.removeHandler(h)

# Cấm root logger propagate ra ngoài
root_logger.propagate = False
```
Chỉ dùng lệnh `print(...)` duy nhất ở cuối hàm `main()` khi và chỉ khi có sự thay đổi thực tế cần thông báo (ví dụ: `created_cnt > 0` hoặc `cleaned_cnt > 0`). Khi không có gì mới, để stdout rỗng 100%.
