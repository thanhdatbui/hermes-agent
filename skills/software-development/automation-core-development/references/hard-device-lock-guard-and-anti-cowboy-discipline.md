# Hard Device Lock Guard & Anti-Cowboy Execution Discipline

## 1. Bối Cảnh & Nguyên Tắc Cốt Lõi
Trên Taadaa Farm (80–280 thiết bị Android), các runner và scheduler tự động (feed session, checklive, avatar upload, 2FA recovery) chạy ngầm liên tục theo chu kỳ.
- **CẤM TUYỆT ĐỐI can thiệp trần vào thiết bị:** Bất kỳ thao tác ADB nào can thiệp thiết bị (`shell`, `push`, `pull`, `install`, `reboot`, `logcat`, `tcpip`, `exec-out`...) hoặc script cấu hình máy đơn lẻ (`set_proxy_farm_adb.py`, `set_wifi_farm_admin_adb.py`...) mà **KHÔNG giữ device lock độc quyền** đều bị coi là hành vi "cao bồi" (Cowboy behavior) và phá vỡ tính toàn vẹn hệ thống.
- **Rủi ro:** Khi thiết bị không bị khóa, batch runner khác tưởng máy rảnh nhảy vào tranh chấp ADB -> vỡ state machine, văng app, gãy kết nối proxy, làm sai lệch trạng thái tài khoản.

## 2. Cơ Chế Hard Guard Tại Runtime (`guard_device_bulkhead.py`)
Pre-tool Hook `D:/Taadaa/tools/hooks/guard_device_bulkhead.py` (đồng bộ tại `~/.hermes/hooks/`) thực thi các nguyên tắc fail-closed:

1. **Compound Statement Boundary Parsing:**
   - Tách toàn bộ các câu lệnh phức hợp theo ranh giới `&&`, `&`, `||`, `;`, `|`, `\n`, `\r` và bóc tách cả subshells lồng nhau `$()`, backticks `` ` ``.
   - Kiểm tra độc lập từng statement: chỉ cần 1 statement vi phạm -> CHẶN TOÀN BỘ command chain ngay lập tức. Chống triệt để chiêu trò nối chuỗi (`adb devices && adb -s ...`).
2. **Default-Deny cho ADB:**
   - Allowlist strictly: `adb devices [-l]`, `adb version`, `adb help`, `adb kill-server`, `adb start-server`, `adb connect/disconnect <IP:port>`, `inspect_machine.py <N>`.
   - Mọi lệnh ADB khác: BẮT BUỘC phải chỉ định rõ `-s <serial>` VÀ serial đó phải có active lock hợp lệ trong `~/.codex/device-locks/`. Không có `-s` -> Bị chặn với `GUARD_AMBIGUOUS_ADB_COMMAND`.
3. **Anti-Forgery & Kernel Process Liveness Check:**
   - Lock file (`serial_<serial>.lock.json`, `machine_<N>.lock.json`) bắt buộc tuân thủ schema protocol version 2 (`status: running`, `owner_active: true`, `lock_id`).
   - Hook đối chiếu PID và kernel process creation timestamp qua `automation_core.device_lock.owner_process_alive(data)` (Win32 `GetProcessTimes` hoặc WMIC `CreationDate`).
   - Mọi file lock tự tạo bằng tay (echo giả mạo) hoặc chứa PID đã chết đều bị REJECT fail-closed.
4. **Anti-Escape Hatch:**
   - Hook chặn toàn bộ các tool execution: `terminal`, `bash`, `shell`, `sh`, `powershell`, `cmd`, `exec`.

## 3. Quy Chuẩn Vận Hành Cho Coordinator
Khi Coordinator cần chẩn đoán, điều tra hiện trường hoặc sửa mạng cho thiết bị:
- **Cách 1 (Từ Terminal/CLI - Khuyên dùng):**
  Bọc qua wrapper script chuẩn:
  ```bash
  python D:/Taadaa/tools/with_device_lock.py --machine <N> -- adb -s <serial> shell ...
  ```
- **Cách 2 (Trong Python Script):**
  Bọc qua context manager của `automation_core`:
  ```python
  from automation_core.device_lock import operator_device_lock

  with operator_device_lock(machine="16", serial="ce011711201cae2704", project="investigate_network"):
      # Các lệnh ADB an toàn ở đây
  ```
- **Cách 3 (Chạy Batch Runner):**
  Chạy qua runner batch chuẩn (`run_tiktok_upload_avatar.ps1`, `run-feed-session.ps1`...) vốn đã tích hợp sẵn `acquire_device_lock`.
