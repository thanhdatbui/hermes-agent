# Module-Level logging.basicConfig Pollution in Watchdog Scripts

## Triệu chứng
Trong các cronjob Hermes chạy chế độ `no_agent: True`, tin nhắn Telegram (Farm Alert) đột ngột bị spam hàng loạt dòng log chi tiết kỹ thuật:
```text
2026-09-22 07:15:27,745 [INFO] [Machine 05 | 9885e64b4a434a3037] Tiến hành gỡ tài khoản ... qua Android OS (skip_lock=True)...
2026-09-22 07:15:27,774 [INFO] AdbClient initialized with remote host=localhost:5037 for serial=9885e64b4a434a3037
2026-09-22 07:15:29,313 [INFO] AdbClient initialized with remote host=localhost:5037 for serial=9885e64b4a434a3037
...
```
Người dùng phàn nàn: *"??? báo clgt ở farm alert"*.

## Cơ Chế Gây Lỗi (Root Cause)
1. **Quy ước `no_agent: True`**:
   - `stdout` rỗng $\rightarrow$ Scheduler coi như im lặng (Silent Watchdog), không gửi gì về Telegram.
   - `stdout` có bất kỳ ký tự nào $\rightarrow$ Toàn bộ nội dung `stdout` được gửi nguyên văn về chat.
2. **Ô nhiễm Root Logger do Import**:
   - Một script helper con (ví dụ: `preflight_s7_rolling_cleanup.py`) có lệnh:
     ```python
     logging.basicConfig(
         level=logging.INFO,
         format="%(asctime)s [%(levelname)s] %(message)s",
         handlers=[logging.StreamHandler(sys.stdout)],
     )
     logger = logging.getLogger("S7RollingCleanup")
```
     đặt ngay ở cấp độ module (ngoài `if __name__ == '__main__':`).
   - Khi script watchdog chính (`sync_gpm_lifecycle.py`) import helper:
     ```python
     from preflight_s7_rolling_cleanup import remove_account_adb
```
     Python thực thi `logging.basicConfig(...)` ở module-level. Lệnh này gắn `StreamHandler(sys.stdout)` vào **Root Logger** của tiến trình.
   - Mọi thư viện/module khác (kể cả `automation_core.adb`, `requests`, `urllib3`) mặc định có `propagate = True`, do đó tất cả log `logger.info()` từ các thư viện này bị đẩy thẳng lên root logger và tuồn ra `sys.stdout`.

## Giải Pháp Chuẩn Hóa

### 1. Trong Thư Viện / Helper Modules
- **CẤM TUYỆT ĐỐI** gọi `logging.basicConfig(handlers=[StreamHandler(sys.stdout)])` ở module-level.
- Cấu hình logger riêng với `FileHandler` và tắt lan truyền:
  ```python
  logger = logging.getLogger("MyModuleName")
  logger.setLevel(logging.INFO)
  logger.propagate = False
  if not logger.handlers:
    _fh = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
    _fh.setFormatter(
        logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
    )
    logger.addHandler(_fh)
```
- Nếu hỗ trợ chạy CLI độc lập, chỉ gắn `StreamHandler(sys.stderr)` bên trong `if __name__ == '__main__':`:
  ```python
  if __name__ == "__main__":
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(
        logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
    )
    logger.addHandler(sh)
    main()
```

### 2. Trong Script Watchdog Entrypoint (`no_agent: True`)
- Luôn chủ động khử trùng (sanitize) Root Logger ngay đầu script:
  ```python
  root_logger = logging.getLogger()
  for h in list(root_logger.handlers):
    if isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) in (
        sys.stdout,
        sys.__stdout__,
    ):
      root_logger.removeHandler(h)
  root_logger.propagate = False
```
- Chỉ dùng đúng một câu lệnh `print(...)` ở cuối ca/khi có hành động thực tế xảy ra. Khi hệ thống ở trạng thái rảnh hoặc không có thay đổi, giữ `stdout` rỗng 100%.
