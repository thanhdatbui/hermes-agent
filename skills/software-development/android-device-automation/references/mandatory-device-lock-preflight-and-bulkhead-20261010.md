# Mandatory Device Lock Preflight & Bulkhead Enforcement (2026-10-10)

## 1. Bối cảnh & Bài học thực tế
Trong phiên xử lý Máy 16 ngày 10/10/2026:
- Khi mạng vừa thông, Coordinator nôn nóng probe hiện trường đã gõ thẳng lệnh `adb shell` trần (bật/tắt Wi-Fi, kiểm tra connectivity, dumpsys...) mà KHÔNG giữ device lock.
- User phát hiện và chấn chỉnh nghiêm khắc: *"khi phát lệnh gì cũng phải lock lại chạy chứ, có cơ chế đó chưa"*.
- Hành vi can thiệp trần này cực kỳ nguy hiểm trên Farm 80–280 máy vì các tiến trình nuôi nick/cronjob nền (PID khác) có thể quét qua máy và nhảy vào chiếm ADB cùng lúc, gây xung đột trạng thái (race condition), văng app, và hỏng tài khoản.

## 2. Hard Gate #5 Cưỡng chế vật lý (guard_device_bulkhead.py)
Hook `D:/Taadaa/tools/hooks/guard_device_bulkhead.py` (đồng bộ vào `C:/Users/Kibe/AppData/Local/hermes/hooks/guard_device_bulkhead.py`) đã kích hoạt Hard Gate:
1. **Chặn lệnh ADB trần:** Mọi lệnh ADB can thiệp thiết bị (`shell`, `push`, `pull`, `install`, `reboot`, `logcat`, `tcpip`, `exec-out`...) BẮT BUỘC phải có `-s <serial>` và máy đó phải có file lock hợp lệ trong `~/.codex/device-locks/`.
2. **Anti-Compound Bypass:** Phân tích câu lệnh theo từng statement thật (`&&`, `&`, `||`, `;`, `|`, `\n`, subshell `$(...)`, backtick `` `...` ``), cấm lách luật bằng cách ghép lệnh vô hại ở đầu chuỗi.
3. **Anti-Forgery & Kernel Validation:** File lock bắt buộc phải có protocol version 2, `status: running`, `owner_active: True`, và đối chiếu timestamp creation date từ OS kernel (`owner_process_alive` qua `GetProcessTimes` WinAPI). File tự tạo giả mạo sẽ bị REJECT ngay lập tức.
4. **Anti-Ambiguous:** Lệnh ADB can thiệp không chỉ định `-s <serial>` bị chặn tuyệt đối.

## 3. Cách thức can thiệp chuẩn mực (How to Execute Safely)
Coordinator hoặc kỹ thuật viên muốn can thiệp máy lẻ BẮT BUỘC dùng 1 trong 3 cách:

### Cách 1: CLI Wrapper (Khuyên dùng)
```bash
python D:/Taadaa/tools/with_device_lock.py --machine 16 -- adb -s ce011711201cae2704 shell getprop ro.serialno
```
Wrapper sẽ tự động xếp hàng chờ (poll 5s) nếu máy đang bận ca nuôi khác, giữ lock độc quyền trong suốt quá trình chạy lệnh, và tự giải phóng khi xong.

### Cách 2: Python Context Manager
```python
from automation_core.device_lock import operator_device_lock

with operator_device_lock(machine="16", serial="ce011711201cae2704", project="fix_m16"):
    # Toàn bộ lệnh can thiệp nằm trong này
```

### Cách 3: Chạy qua Runner Batch chuẩn
Các file PowerShell như `run_tiktok_upload_avatar.ps1`, `run-feed-session.ps1` đã tích hợp sẵn cơ chế lock bên trong.

### Các lệnh được miễn trừ (Read-only Allowlist):
- `adb devices`, `adb version`, `adb help`, `adb kill-server`, `adb connect <IP>`.
- Trích xuất hiện trường O(1): `python D:/Taadaa/tools/inspect_machine.py <N>`.
