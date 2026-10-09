# Teardown về HOME và Pitfall khi Patch Code Multi-Machine Feed Session

## 1. Quy tắc Teardown về HOME & Force-Stop TikTok (`multi_machine_feed_session.py`)
- **Mục đích:** Tránh thiết bị bị ngâm màn hình feed/profile/video sau khi session kết thúc (hoàn thành bình thường, follow timeout hoặc unhandled exception), dẫn đến nhả follow hoặc gây nghi ngờ cho thuật toán TikTok.
- **Cơ chế:**
  - Định nghĩa hàm `_force_stop_tiktok_and_home(child_ctx, serial=..., adb_path=...)`:
    1. Ưu tiên qua `child_ctx.adb.shell(["am", "force-stop", target_package])` và `child_ctx.adb.shell(["input", "keyevent", "3"])`.
    2. Fallback qua `subprocess.run([adb_path, "-s", serial, "shell", ...])`.
  - Được gọi ở 2 vị trí quan trọng:
    1. Timeout handler trong `_run_follow_hook`.
    2. Khối `finally:` của `_run_child` trong `multi_machine_feed_session.py`, ngay trước khi nhả lease (`lock_holder.get("lease")`).

## 2. Pitfall khi Patch Code Windows Paths
- Khi dùng tool find/replace patch code Python có chứa raw string đường dẫn Windows (ví dụ `r"D:\Taadaa\tiktok-follow\follow_runner\run_follow.py"`):
  - Chuỗi `\run` có thể bị unescape thành `\r` (carriage return/newline) trong quá trình parse JSON/escape chuỗi, dẫn tới `SyntaxError: unterminated string literal`.
  - **Giải pháp:** Sử dụng forward slash `D:/Taadaa/...` hoặc kiểm tra kỹ escape double backslashes `\\` khi thực hiện patch script.
