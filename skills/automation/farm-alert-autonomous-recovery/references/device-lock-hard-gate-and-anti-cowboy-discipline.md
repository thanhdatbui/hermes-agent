# Kỷ Luật Cưỡng Chế Device Lock & Chống Cowboy Khi Điều Phối Farm (2026-10-09)

## 1. Bối cảnh & Sai lầm thực tế (The Cowboy Trap)
- **Tình huống:** Khi mạng Viettel/Singbox vừa được khôi phục, Coordinator nôn nóng probe thiết bị Máy 16 (`ce011711201cae2704`) nên đã phát trực tiếp các lệnh ADB trần (`adb -s ... shell svc wifi disable`, `dumpsys connectivity`...) trên terminal session mà KHÔNG hề giữ device lock.
- **Hậu quả & Rủi ro P0:** Trên Farm 80–280 máy, các tiến trình nền (cronjob feed session, tiktok upload, reg mail...) liên tục quét tìm máy rảnh. Nếu Coordinator can thiệp trần không lock, cronjob sẽ chiếm máy song song gây xung đột socket, crash app TikTok, corrupt state machine và làm hỏng tài khoản.
- **Nguyên nhân gốc rễ:** Trước đây cơ chế `acquire_device_lock` chỉ được tích hợp bên trong các file kịch bản batch (PowerShell / Python state machine). Ở tầng terminal của Coordinator hoàn toàn không có chốt chặn vật lý nào, dẫn đến việc bỏ qua kỷ luật khi gặp áp lực công việc.

## 2. Hard Gate Enforce tại Hook `guard_device_bulkhead.py`
Để không phụ thuộc vào "ý thức tự giác" của AI, toàn bộ lệnh terminal can thiệp thiết bị đã được cưỡng chế vật lý tại `D:/Taadaa/tools/hooks/guard_device_bulkhead.py`:

### A. Phân tách ranh giới câu lệnh thật (Compound Statement Splitting)
- CẤM regex matching trên toàn chuỗi lệnh vì dễ dính **Chaining bypass** (ví dụ: `adb devices && adb -s SERIAL shell input tap ...` lợi dụng lệnh vô hại đầu dòng để lách gate).
- Hook phân tách lệnh theo các toán tử shell: `&&`, `&`, `||`, `;`, `|`, `\n`, `\r`, đồng thời trích xuất subshells `$(...)` và backticks `...`.
- Mỗi statement được thẩm định độc lập theo nguyên tắc **Fail-Closed**: chỉ cần 1 statement vi phạm là toàn bộ chuỗi lệnh bị chặn đứng.

### B. Default-Deny cho ADB
- Chỉ cho phép các lệnh server vô hại: `adb devices`, `adb version`, `adb help`, `adb kill-server`, `adb start-server`, `adb connect`, `adb disconnect`.
- Script trích xuất hiện trường read-only O(1): `python D:/Taadaa/tools/inspect_machine.py <N>`.
- Mọi lệnh ADB can thiệp thiết bị khác:
  1. BẮT BUỘC phải chỉ định rõ serial: `-s <serial>` (CẤM lệnh mơ hồ `adb shell ...` trên farm nhiều máy).
  2. BẮT BUỘC phải có active lock file hợp lệ trong `~/.codex/device-locks/`.

### C. Cơ chế chống giả mạo Lock (Anti-Forgery & Kernel Validation)
- Không chỉ đọc nội dung file JSON tự khai báo (`status: running`, `owner_active: True`).
- Bắt buộc kiểm tra `owner_process_alive(data)` trong `automation_core.device_lock`:
  - Đối chiếu kernel creation timestamp của tiến trình qua Windows API (`OpenProcess` -> `GetProcessTimes` -> `FILETIME` -> UTC datetime) hoặc WMIC fallback.
  - Nếu file lock bị giả mạo hoặc tiến trình giữ lock đã chết -> BỊ CHẶN NGAY LẬP TỨC.

### D. Chuẩn hóa Input Boundary & Default-Deny Script
- `is_bg` kiểm tra kiểu nghiêm ngặt (chống truthy string `"false"` lọt qua).
- `timeout` được ép kiểu an toàn chống `TypeError`.
- Không hardcode danh sách tên script `.ps1` mà bắt mọi cờ targeting máy (`-Machines`, `-TargetMachines`, `--machine`...) và pattern script farm (`run-*`, `batch-*`, `tiktok-*`, `farm-*`).

## 3. Workflow Chuẩn cho Coordinator khi Can Thiệp Thiết Bị
Khi cần chạy lệnh chẩn đoán hoặc can thiệp riêng lẻ trên máy thật:
- **Cách 1 (Khuyên dùng cho shell/CLI):** Bọc qua CLI wrapper chuẩn:
  ```bash
  python D:/Taadaa/tools/with_device_lock.py --machine <N> -- <command...>
  ```
- **Cách 2 (Khuyên dùng trong Python script):** Bọc qua context manager:
  ```python
  from automation_core.device_lock import operator_device_lock

  with operator_device_lock(machine="<N>", serial="<SERIAL>", project="operator_fix"):
      # Toàn bộ thao tác ADB/Preflight/Repair nằm trong này
  ```
- **Cách 3:** Chạy qua các runner batch chuẩn của farm (`run_tiktok_upload_avatar.ps1`, `run-feed-session.ps1`...).
