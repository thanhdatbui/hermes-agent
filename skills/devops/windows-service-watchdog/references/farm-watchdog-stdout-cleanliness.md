# Farm Maintenance & Watchdog Cleanliness Reference

## 1. Silent Watchdog stdout Cleanliness (no_agent=True)
- Trong các cronjob `no_agent: true`, bất kỳ dòng log nào lọt ra `stdout` đều được Hermes Gateway đóng gói thành tin nhắn gửi đến người dùng (Telegram).
- Khi gọi thư viện bên ngoài hoặc chạy đa luồng (`ThreadPoolExecutor`):
  - `contextlib.redirect_stdout` không an toàn luồng (thread-unsafe).
  - Phải gỡ bỏ hoàn toàn handlers của root logger và gán `NullHandler()` cho logger module con (`propagate = False`).
  - Phải bọc cả `redirect_stdout` lẫn `redirect_stderr`.
  - Khóa chặt điều kiện báo cáo: NẾU `len(success_list) == 0` thì watchdog bắt buộc im lặng hoàn toàn (`return 0`), cấm in tiêu đề hoặc danh sách thất bại ra stdout.

## 2. ADB Command stdout/stderr Cleanliness
- Các lệnh shell quản lý package trên thiết bị (`pm disable-user`, `pm uninstall`) nếu gọi vào package không tồn tại trên dòng máy (ví dụ `com.samsung.android.spay` trên máy thiếu Samsung Pay) sẽ trả về `Error: java.lang.IllegalArgumentException: Unknown package` ra stdout/stderr.
- Cần chuyển hướng `stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL` hoặc kiểm tra sự tồn tại của package trước khi gọi để tránh làm bẩn stdout của cron watchdog.

## 3. Python xml.etree Element Boolean Pitfall
- Trong Python: `bool(xml.etree.Element) == False` nếu phần tử đó không có con.
- Kiểm tra node XML bắt buộc dùng `if node is None:` thay vì `if not node:`.
