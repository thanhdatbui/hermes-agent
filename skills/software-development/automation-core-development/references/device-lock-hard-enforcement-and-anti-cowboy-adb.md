# Device Lock Hard Enforcement & Anti-Cowboy ADB Invariants (2026-10-09)

## 1. Bối cảnh & Hiện trường Vi phạm
Trong các phiên điều tra và can thiệp máy farm lẻ, Coordinator thường mắc lỗi "chữa cháy nhanh" (Cowboy Engineering):
- Tự ý gõ các lệnh ADB trực tiếp (`adb -s <serial> shell ...`, `dumpsys wifi`, `svc wifi disable/enable`, `cmd wifi ...`) mà **không hề bọc qua cơ chế Device Lock**.
- **Nguy cơ thảm họa:** Trên farm 80-280 máy, các cronjob định kỳ và runner batch chạy ngầm liên tục quét tìm máy rảnh. Khi can thiệp trần, cronjob tưởng máy rảnh nhảy vào chiếm ADB cùng lúc -> Race condition, xung đột UI, văng session TikTok, cướp mạng gây flag nick.

---

## 2. Bất biến Cấm Can thiệp Trần (Zero Bare-ADB Invariant)
1. **CẤM TUYỆT ĐỐI** phát lệnh ADB can thiệp thiết bị thật khi chưa có active lock trong `~/.codex/device-locks/`.
2. Mọi thao tác can thiệp thiết bị lẻ từ Coordinator BẮT BUỘC phải thực hiện theo 1 trong các cách chuẩn:
   - **Cách 1 (CLI Wrapper):**
     ```bash
     python D:/Taadaa/tools/with_device_lock.py --machine <N> -- <command...>
     ```
   - **Cách 2 (Python Context Manager):**
     ```python
     from automation_core.device_lock import operator_device_lock
     with operator_device_lock(machine=str(mach_id), serial=serial, project="manual_debug"):
         # Toàn bộ lệnh can thiệp nằm trong này
     ```
   - **Cách 3 (Batch Runner):** Chạy qua runner chuẩn (`run_tiktok_*.ps1`, `run-feed-session.ps1`...).

---

## 3. Kiến trúc Cưỡng chế Vật lý: Hard Gate #5 (`guard_device_bulkhead.py`)
Cơ chế kiểm soát tại Pre-tool Hook (`D:/Taadaa/tools/hooks/guard_device_bulkhead.py`) chặn đứng mọi nỗ lực can thiệp vi phạm:

1. **Phân tích ranh giới câu lệnh thật (Compound Statement Splitting):**
   - Tách toàn bộ chuỗi lệnh theo các toán tử: `&&`, `&`, `||`, `;`, `|`, `\n`, `\r`, cùng subshells `$()` và backticks `` ` ``.
   - Thẩm định độc lập từng statement: Chỉ cần 1 statement vi phạm là chặn toàn bộ command chain (chống kỹ thuật bypass nối chuỗi `adb devices && adb shell ...`).
2. **Default-Deny cho ADB:**
   - Chỉ duy nhất các lệnh server-level vô hại (`devices`, `version`, `kill-server`, `start-server`, `connect`, `disconnect`) hoặc script trích xuất O(1) `inspect_machine.py` mới được phép chạy không cần lock.
   - MỌI lệnh ADB khác bắt buộc phải chỉ định `-s <serial>` và thiết bị đó phải có active lock. Lệnh thiếu `-s` bị chặn với `GUARD_AMBIGUOUS_ADB_COMMAND`.
3. **Chống giả mạo Lock (Anti-Forgery & Kernel Validation):**
   - Lock file trong `~/.codex/device-locks/` bắt buộc phải có protocol version 2, `status == 'running'`, `owner_active is True`.
   - Đối chiếu creation timestamp thực tế từ kernel OS qua `automation_core.device_lock.owner_process_alive()` (sử dụng WinAPI `OpenProcess` -> `GetProcessTimes` -> `FILETIME`).
   - File giả mạo hoặc tiến trình đã chết (dead PID) đều bị từ chối ngay lập tức.
4. **Bulkhead Foreground Timeout:**
   - Mọi thao tác chạy lệnh điều khiển thiết bị ở chế độ Foreground bắt buộc phải có `timeout <= 60s`.
   - Tác vụ dài (> 60s) bắt buộc phải chạy Background (`background=True, notify_on_complete=True`).
