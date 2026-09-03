# Operator Preempt Device Lock Contract (2026-08-22)

## 1. Bối cảnh & Vấn đề
- **Xung đột giữa Cron nền và Thao tác can thiệp tay / Batch ưu tiên:**
  - Cron nền (như `multi-machine-feed-session`) chạy đa luồng định kỳ, giữ device lock (`owner_active=True`, PID đang chạy).
  - Khi Operator chạy các script can thiệp tức thì (Hotmail login, Reg TikTok, 2FA, debug một máy cụ thể), cơ chế `FULL_SCOPE_TAKEOVER` thông thường sẽ bị chặn nếu process của cron nền vẫn còn `alive` (`alive is not False`), dẫn đến việc script không lấy được lock hoặc cả 2 tiến trình cùng tương tác ADB lên thiết bị gây xung đột UI (như trường hợp Outlook mở đè lên màn hình TikTok gây `profile verification mismatch`).

## 2. Giải pháp Core: `OPERATOR_PREEMPT` & `force_preempt=True`
- Trong `automation_core.device_lock`:
  - Thêm hằng số `TAKEOVER_SCOPE_OPERATOR_PREEMPT = "OPERATOR_PREEMPT"`.
  - Cập nhật `_validate_takeover_request()` và `_takeover_payload()`: Cho phép cướp quyền lock ngay cả khi owner cũ đang ở trạng thái active (`status in ("running", "queued", "recovery")` và process PID đang sống).
  - Thêm cờ `force_preempt: bool = False` vào `acquire_device_lock()` và `DeviceLock.__init__()` (vị trí cuối cùng trong danh sách keyword-only arguments để bảo toàn backward-compatibility contract của tham số vị trí).
  - Ghi nhận snapshot của owner bị cướp vào trường `takeover_from` trong lock payload:
    ```json
    {
      "takeover_from": {
        "pid": 12345,
        "project": "multi-machine-feed-session",
        "status": "running",
        "lock_id": "..."
      },
      "takeover_authorization": {
        "scope": "OPERATOR_PREEMPT",
        "reason": "..."
      }
    }
    ```

## 3. Quy chuẩn sử dụng trên Consumer Repos (All-Repo Standard)
Mọi script chạy theo lệnh Operator cần chiếm quyền ưu tiên phải tuân thủ mẫu chuẩn 3 bước:
```python
from automation_core.device_lock import DeviceLock

with DeviceLock(
    serial=serial,
    machine=m,
    project="<script-project-name>",
    force_preempt=True,
    takeover_reason="operator priority run",
    bypass_proxy_readiness=True,
    user_authorized=True,
):
    # Bước 1: Ngắt app nền trên đúng máy đích (Targeted stop)
    subprocess.run([adb_path, "-s", serial, "shell", "am", "force-stop", "com.ss.android.ugc.trill"], capture_output=True)
    
    # Bước 2: Thao tác tác vụ chính của script
    status = execute_task(...)
    
    # Bước 3: Dọn dẹp app của script và trả máy về màn hình chính
    subprocess.run([adb_path, "-s", serial, "shell", "am", "force-stop", "<app_package>"], capture_output=True)
    subprocess.run([adb_path, "-s", serial, "shell", "input", "keyevent", "3"], capture_output=True)
```

## 4. Đặc điểm cách ly đa luồng
- Cơ chế `force_preempt` kết hợp với `adb -s <serial> ...` đảm bảo **chỉ dừng luồng chạy trên duy nhất máy mục tiêu**.
- Toàn bộ các worker threads khác trong batch cron nuôi acc (các máy khác trong farm) vẫn tiếp tục chạy độc lập và về đích bình thường, không bị gián đoạn.
