# No-Agent Cron Silent Watchdog & Farm Alert Discipline

## 1. Bản chất cơ chế `no_agent: true` trong Hermes Cron
- **Semantics**:
  - Khi script chạy trên schedule với `no_agent: true`, scheduler không gọi LLM mà chỉ bắt `stdout` của script.
  - BẤT KỲ dữ liệu nào in ra `sys.stdout` (dù là log INFO, ERROR, hay traceback) đều được gửi nguyên văn (verbatim) vào Telegram target (`origin` hoặc nhóm Farm Alert).
  - Chỉ khi `stdout` **hoàn toàn trống (0 bytes)** thì cron mới im lặng (Watchdog pattern).

## 2. Cạm bẫy rò rỉ log gây spam Telegram (Root Cause)
- Script watchdog thường import các module/thư viện con (như GPM automation, ADB runner, CDP client, S7 rolling cleanup).
- Các thư viện con này thường cấu hình:
  ```python
  logging.basicConfig(handlers=[..., logging.StreamHandler(sys.stdout)])
  ```
- **Hậu quả kép**:
  + Khi xảy ra lỗi (ví dụ GPM Start API lệch version Chromium, timeout ADB, proxy chết), thư viện con tự động in các dòng `[ERROR]` ra stdout.
  + Ngay cả khi chạy bình thường (ví dụ dọn tài khoản S7: `preflight_s7_rolling_cleanup.py`), lệnh `logging.basicConfig(handlers=[StreamHandler(sys.stdout)])` ở top-level của thư viện con khi import sẽ chiếm đoạt root logger của toàn bộ tiến trình. Hàng chục dòng log info bình thường (`[INFO] [Machine 05] Tiến hành gỡ...`, `[INFO] AdbClient initialized...`, `[INFO] Máy M07 đang trong slot feed, bỏ qua...`) bị tuôn xối xả ra `stdout`.
- Kết quả: Cron tick mỗi 15 phút bắn liên tiếp các dump log debug/info nội bộ này về Farm Alert Telegram khiến người dùng bực mình. Mọi helper/thư viện BẮT BUỘC chỉ cấu hình StreamHandler bên trong `if __name__ == '__main__':`.

## 3. Kỷ luật thông báo Farm Alert (User Invariant)
- **Vẫn gửi về nhóm Farm Alert (`telegram:-5373649734`)**: Không được ngắt hoàn toàn delivery hay chuyển vĩnh viễn sang local khi user vẫn cần nhận kết quả hoàn tất.
- **CẤM spam tiến trình**: Tuyệt đối không gửi log từng bước, log xử lý từng máy, hay log exception lặp đi lặp lại.
- **Báo cáo ngắn gọn khi thành công**: Chỉ in ra stdout duy nhất một khối tóm tắt khi có kết quả hành động thực tế (`success_list > 0`). Khi không có thay đổi hoặc toàn bộ lỗi: im lặng 100%.

## 4. Mẫu bọc cách ly stdout tuyệt đối (Silent Isolation Pattern)
Áp dụng mẫu bọc sau trong hàm loop của watchdog trước khi gọi thư viện con:

```python
import io
import contextlib
import logging

success_list = []
fail_list = []

for item in candidates:
    try:
        # Bịt kín toàn bộ stdout/stderr và vô hiệu hóa logging từ module con
        f_null = io.StringIO()
        prev_disable = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        try:
            with contextlib.redirect_stdout(f_null), contextlib.redirect_stderr(f_null):
                res = external_submodule_action(item)
        finally:
            logging.disable(prev_disable)

        if res.get("status") == "SUCCESS":
            success_list.append(item)
        else:
            fail_list.append((item, res.get("details")))
    except Exception as e:
        fail_list.append((item, str(e)))

# CHỈ in ra stdout khi có thành công thực sự để gửi Telegram ngắn gọn
if success_list:
    report = [
        "### [BÁO CÁO HOÀN TẤT]",
        f"- Thành công: {len(success_list)} items",
        f"- Cần lưu ý: {len(fail_list)} items" if fail_list else ""
    ]
    print("\n".join(filter(None, report)))
# Nếu success_list rỗng: stdout tự động là 0 bytes -> Cron giữ im lặng tuyệt đối.
```
