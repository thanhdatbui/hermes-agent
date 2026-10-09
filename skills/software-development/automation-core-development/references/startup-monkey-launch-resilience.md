# Startup Monkey Launch Resilience & Testing Pitfalls

## 1. Bối cảnh & Vấn đề
Trong `automation_core.startup.prepare_app_for_automation`, việc khởi chạy app thông qua `adb.shell(["monkey", "-p", target, "-c", "android.intent.category.LAUNCHER", "1"])` có thể gặp các vấn đề thực chiến trên farm:
- Nếu ứng dụng mục tiêu đã ở foreground, việc bắn intent monkey một lần nữa gây giật lag hoặc khởi động lại app không cần thiết.
- Trên các máy cấu hình thấp hoặc ADB daemon bị nghẽn, lệnh monkey có thể bị timeout hoặc văng `ADBError` dù thực tế ứng dụng đã được khởi động và đang hiển thị trên màn hình.
- Trong vòng lặp kiểm tra focus (retry monkey tại attempt 4, 7), nếu không bọc `try...except`, một timeout đột ngột từ ADB sẽ làm crash toàn bộ tiến trình startup.

## 2. Quy chuẩn triển khai trong `prepare_app_for_automation`
- **Pre-launch Foreground Check:** Trước khi gọi monkey, đọc `cur_pkg, cur_act = focus_reader()`. Nếu `cur_pkg == target`: ghi nhận `StartupStep("launch_app", "success", "", {"package": target, "status": "already_foreground"})` và tiếp tục verify mà không gọi monkey.
- **Tối thiểu timeout & bắt Exception:** Khi gọi monkey, áp dụng `timeout=max(timeout, 30.0)` và bọc trong `try...except Exception as exc:`. Nếu có exception/timeout, kiểm tra lại `cur_pkg, _ = focus_reader()`. Nếu `cur_pkg == target` thì vẫn ghi nhận khởi chạy thành công.
- **Guarded retry trong verify loop:** Tại attempt 4, 7, gọi monkey bên trong khối `try...except Exception: pass` với `timeout=max(timeout, 30.0)`.

## 3. Cạm bẫy Unit Test (Test Pitfalls)
- **Mock static `focus_reader`:** Các test cũ thường mock `focus_reader = lambda: ("com.example.target", "MainActivity")`. Khi có logic kiểm tra foreground trước monkey, monkey sẽ bị bỏ qua (skipped).
- **Hệ quả:** Nếu test kiểm tra số lượng gọi ADB shell hoặc danh sách timeout (ví dụ `assert adb.timeouts == [60, 60]`), test sẽ fail vì thiếu lượt gọi monkey (`[60]` thay vì `[60, 60]`).
- **Cách khắc phục chuẩn:** Đối với các test cần kiểm tra hành vi monkey, mock `focus_reader` trả về trạng thái Launcher/khác ở lần gọi đầu tiên và target package ở các lần gọi sau:
  ```python
  focus_states = ["com.android.launcher", "com.example.target"]
  focus_reader = lambda: (focus_states.pop(0) if focus_states else "com.example.target", "MainActivity")
  ```
- **Bổ sung test đặc thù:** Luôn có test riêng kiểm chứng nhánh `already_foreground` (xác nhận monkey không được gọi) và nhánh `monkey exception recovery` (xác nhận app vẫn startup thành công nếu focus đạt chuẩn).
