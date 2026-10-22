# Android Framework Settings Service Probe & Pre-Session Gate Hardening (2026-10-22)

> Incident 2026-10-22: Máy 213 (Admin) báo "Mất kết nối Wi-Fi (AP)" trên báo cáo Feed Watchdog, nhưng thực tế Wi-Fi có IP 192.168.110.87. Lỗi do Android `system_server` / `settings` service bị crash (`cmd: Can't find service: settings`).

---

## 1. Bản Chất Kỹ Thuật: Điểm Mù Của `adb get-state`

- **Sự khác biệt 2 tầng trong kiến trúc Android:**
  1. *Tầng Linux Kernel & Native Daemon (`adbd`):* Viết bằng C, chạy độc lập dưới quyền root/shell. Khi `system_server` (Android Java Framework) chết hoặc treo, `adbd` vẫn sống và kết nối socket USB bình thường. Lệnh `adb -s <serial> get-state` chỉ hỏi daemon `adbd` nên trả về `device` (xanh lè).
  2. *Tầng Android Java Framework (`system_server` / `servicemanager`):* Quản lý các dịch vụ cốt lõi như `settings`, `activity`, `package`, `wifi`, `connectivity`. Khi dịch vụ `settings` bị crash:
     - Lệnh `settings get global http_proxy` hoặc `settings put system screen_off_timeout` trả về `cmd: Can't find service: settings`.
     - App runner không đọc được cấu hình proxy, bị block ở `vpn_preflight.py` và gán nhãn `blocked-proxy-vpn` hoặc rớt mạng.

- **Tại sao Runner Trong Ca Không Thể Cứu:**
  - In-flight self-healing trong ca (`vpn_preflight.py`) chỉ được phép gọi `adb reconnect` (reset socket USB). Lệnh này không thể hồi sinh được `system_server`.
  - Khôi phục `Can't find service: settings` bắt buộc phải reboot thiết bị S7 (Level 2 reboot bypass shell qua `adb reboot`).
  - Trong ca nuôi đang chạy, một lần reboot S7 mất 45–60 giây. Nếu worker tự ý reboot sẽ gây timeout worker thread, nghẽn I/O bus và bão DHCP ảnh hưởng các máy khác trong batch. Runner bắt buộc phải fail-fast ngắt máy lỗi để cứu tiến độ ca.

---

## 2. Giải Pháp Chuẩn Hóa: Thăm Dò 2 Tầng Trong `pre_session_device_gate.py`

- **Kiến trúc thăm dò 2 tầng O(1):**
  1. *Tầng 1 (Kernel Socket):* `adb -s <serial> get-state` (timeout 3.0s). Nếu khác `device` -> xử lý rớt ADB/USB.
  2. *Tầng 2 (Framework Responsiveness):* Ngay khi Tầng 1 trả về `device`, phát tiếp lệnh nhẹ kiểm tra dịch vụ `settings`:
     ```bash
     adb -s <serial> shell service check settings (timeout 2.0s)
     ```
- **Tiêu chuẩn kiểm tra nghiêm ngặt (Anti-False-Positive):**
  - Trạng thái thành công: `returncode == 0`, `bool(stdout) == True`, `"found" in stdout.lower()` VÀ `"not found" not in stdout.lower()`.
  - Phản hồi chuẩn: `Service settings: found`.
  - Bắt dứt điểm các lỗi: `Service settings: not found`, `cmd: Can't find service: settings`, stdout rỗng hoặc shell timeout.
- **Telemetry có cấu trúc:**
  - Bắn sự kiện `framework_check` kèm `serial`, `machine_id`, `status` (`success`, `failure`, `timeout`, `error`), và `latency_sec`.
- **Cứu hộ tự động trước ca:**
  - Khi phát hiện `framework_unresponsive`, quy trình `probe_and_recover_device()` tự động kích hoạt Level 2 direct reboot cứu máy và re-probe trước khi batch nuôi phát lệnh.

---

## 3. Kỷ Luật Diff Budget Sizing (30KB Gate Cap) Khi Đưa Tool Mới Qua Closeout Gate

- **Bẫy Untracked File:**
  - Khi một tool mới gồm file code + test suite (> 30KB) ở trạng thái untracked (`??`), `closeout_gate.py` trích xuất 100% dung lượng file làm diff so với `origin/main` -> vượt ngưỡng `MAX_DIFF_BYTES_GATE = 30_000` bytes.
  - Reviewer Sol High bị cắt diff dở dang và trả về `NEED_CONTEXT:<file>(partial)`.
- **Quy trình chuẩn hóa 2 bước đưa vào Git:**
  1. *Bước 1 (Commit Baseline):* Commit toàn bộ phiên bản gốc của tool và test suite vào git trước (`feat(...): baseline ...`).
  2. *Bước 2 (Commit Surgical Fix):* Áp dụng bản vá phẫu thuật O(1) lên trên và commit làm `HEAD` (`fix(...): ... [gate-approved]`).
  3. *Bước 3 (Thẩm định scoped):* Chạy `closeout_gate.py --repo <repo> --base HEAD~1 --files <impl.py> <test.py> --json-output`. Diff của `HEAD~1..HEAD` chỉ còn vài chục dòng (< 12KB), đảm bảo Reviewer nhận đủ 100% context mà không bị cắt xén.
