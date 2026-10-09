# Farm Device Lock Discipline & Terminal Guardrails (Updated 2026-10-10)

## 1. Bối cảnh
Trên farm 80-280 máy, các cronjob nuôi nick (`run_tiktok.py --mode multi-machine-feed-session`), batch upload avatar, reg, 2FA liên tục quét tìm máy rảnh.
Nếu Coordinator hoặc Worker chạy lệnh can thiệp trần (`adb -s <serial> shell ...`, probe mạng, đổi Wi-Fi) mà **không giữ device lock**:
- Gây xung đột race condition với các tiến trình nền.
- Làm crash app, gián đoạn ca nuôi hoặc gây văng nick.

## 2. Hard Gate Cưỡng chế Vật lý (`guard_device_bulkhead.py`)
Tại pre-tool hook của terminal:
1. **P0-2 (Cấm bấm tay ADB):** Chặn tuyệt đối `adb shell input tap/swipe/keyevent/text`.
2. **Device Lock Required (Anti-Cowboy, Fail-Closed):**
   - Phân tích cú pháp theo ranh giới câu lệnh thật (`&&`, `||`, `;`, `|`, newline, subshell `$()`, backticks).
   - Duyệt độc lập từng statement: một statement vi phạm là block toàn bộ chain.
   - **Default-Deny cho ADB:** Mọi lệnh ADB ngoài server allowlist (`devices`, `version`, `kill-server`, `connect`...) bắt buộc phải có `-s <serial>` và máy đó phải có file lock hợp lệ trong `~/.codex/device-locks/`.
   - **Anti-Forgery & Kernel Validation:** File lock bắt buộc phải có schema protocol v2, `running`, `owner_active: True`, `lock_id`, và được đối chiếu kernel creation timestamp qua `owner_process_alive()` (WinAPI `GetProcessTimes` & WMIC `CreationDate`). Lock giả mạo hoặc PID chết bị reject ngay lập tức.
3. **Zero-Foreground Bulkhead:** Mọi script điều khiển thiết bị (`run-*`, `batch-*`, `tiktok-*`, `farm-*`, flag `-Machines`, `-TargetMachines`, `-Devices`) chạy foreground bắt buộc timeout <= 60s; nếu chạy dài bắt buộc `background=True, notify_on_complete=True`.
4. **Device Circuit Breaker:** Máy thất bại 3 lần liên tiếp bị cách ly (Quarantine 15 phút cooldown).

## 3. Cách Sử dụng Chuẩn cho Coordinator / Operator
Khi cần can thiệp hoặc chẩn đoán thiết bị máy N:
- **Cách 1 (CLI Wrapper):**
  ```bash
  python D:/Taadaa/tools/with_device_lock.py --machine <N> -- <command...>
  ```
  Wrapper sẽ tự động xếp hàng chờ ca nuôi xong, giữ lock độc quyền và giải phóng khi lệnh kết thúc.
- **Cách 2 (Python Context Manager):**
  ```python
  from automation_core.device_lock import operator_device_lock

  with operator_device_lock(machine=N, serial=SERIAL, project="operator_fix"):
      # Thực thi thao tác ADB / Preflight tại đây
  ```
- **Cách 3 (Batch Runner Chuẩn):**
  Chạy qua các file runner batch (`run_tiktok_upload_avatar.ps1`, `run-feed-session.ps1`...) với `background=True`.
