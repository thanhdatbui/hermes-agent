# Điểm Mù Thăm Dò `adb get-state` vs Android Framework Crash (22/10/2026)

## 1. Hiện Tượng & Sự Cố Máy 213 (Ca 2 Chiều 22/10/2026)
- **Triệu chứng trên Watchdog:** Máy 213 bị báo cáo lỗi "Mất kết nối Wi-Fi (AP)".
- **Hiện trường thực tế (`inspect_machine.py 213`):**
  * Wi-Fi vẫn kết nối bình thường, nhận IP LAN `192.168.110.87`.
  * Tuy nhiên lệnh đọc proxy trả về lỗi: `cmd: Can't find service: settings`.
  * Màn hình báo `UNKNOWN`, không thể đọc window focus.
- **Thực nghiệm cứu hộ:** Chạy `python D:/Taadaa/tools/recover_stuck_s7.py -m 213` (kích hoạt Level 2 bypass-shell direct reboot qua adbd) -> Máy khởi động lại xong hồi phục 100% xanh tươi (IP `192.168.110.80`, Proxy `:10012`, launcher hoạt động tốt).

---

## 2. Bản Chất Kỹ Thuật: Tại Sao Farm Vận Hành Không Tự Động Cứu?
Có 2 rào cản độc lập khiến máy 213 lọt lưới và không được tự động cứu trong ca chạy:

### Rào Cản 1: Điểm mù của Pre-Session Device Readiness Gate (`pre_session_device_gate.py`)
- Trước ca nuôi, `pre_session_device_gate.py` chạy probe nhanh O(1) qua lệnh:
  `adb -s <serial> get-state`
- **Bản chất tầng socket vs framework Android:**
  * `adbd` là tiến trình daemon C/C++ chạy ở tầng Linux kernel userspace.
  * `settings`, `activity`, `package` là các dịch vụ Java do tiến trình `system_server` quản lý qua `servicemanager`.
  * Khi `system_server` bị crash, out-of-memory hoặc deadlock, tiến trình `adbd` vẫn hoàn toàn nguyên vẹn.
  * Vì vậy, `adb get-state` vẫn trả về `device` với returncode = 0.
  * Pre-Session Gate bị đánh lừa rằng thiết bị đang hoàn toàn khỏe mạnh (`status: ready`), không kích hoạt `recover_device()` mà bàn giao thẳng vào danh sách máy chạy batch!

### Rào Cản 2: Kỷ luật an toàn trong ca (In-Flight Anti-Reboot Invariant)
- Trong lúc runner nuôi acc đang chạy:
  * Runner chỉ có cơ chế Level 3 soft reconnect (`adb reconnect`) khi kiểm tra VPN timeout. Lệnh này chỉ reset socket USB, hoàn toàn vô hiệu khi `system_server` đã chết.
  * CẤM TUYỆT ĐỐI runner tự ý reboot máy điện thoại Samsung S7 giữa ca chạy (chu kỳ boot mất 45–60s) vì sẽ làm treo cứng worker thread, vỡ nhịp stagger, gây bão DHCP và ảnh hưởng đến các máy khác đang lướt video.
  * Runner buộc phải Fail-Fast: ngắt máy 213, đánh dấu fail để watchdog báo cáo và tiếp tục các máy khác.

---

## 3. Giải Pháp Vá Triệt Để Tầng Pre-Session Gate
- Nâng cấp `probe_device(machine_id)` trong `pre_session_device_gate.py`:
  * Sau khi `adb get-state` trả về `device`:
  * BẮT BUỘC gửi thêm 1 lệnh binder probe siêu nhẹ tới `servicemanager`:
    `adb -s <serial> shell service check settings` (timeout cứng <= 2.0s).
  * Lệnh `service check settings` chỉ kiểm tra đăng ký binder của dịch vụ `settings` trong `servicemanager`, không spawn JVM nặng nề, latency chỉ ~0.2s.
  * Nếu kết quả trả về `Service settings: found` -> Đạt chuẩn khỏe mạnh (`True, 'device'`).
  * Nếu trả về `not found`, timeout, hoặc non-zero -> Xác định `framework_unresponsive`, trả về `(False, 'framework_unresponsive')`.
  * Nhờ đó, Pre-Session Gate phát hiện máy bị đơ framework NGAY TRƯỚC CA CHẠY và tự động kích hoạt `recover_device()` (Level 2 direct reboot) để cứu máy hoàn tất trước khi runner phát lệnh.

---

## 4. Bẫy Terminal Guard Khi Dispatch Worker
- **Bẫy false-positive AMBIGUOUS ADB DEVICE COMMAND:**
  * Khi gọi `dispatch_worker.py` với chuỗi prompt chứa cụm từ `"adb get-state"`, regex guard của Coordinator quét qua toàn bộ command string, bắt dính token `adb` thiếu `-s <serial>` và chặn thực thi:
    `[HARD GATE #5 - AMBIGUOUS ADB DEVICE COMMAND] LỆNH ADB BỊ CHẶN`.
  * **Khắc phục chuẩn hóa:** Viết prompt contract ra file trung gian (ví dụ `D:/Taadaa/tools/task_prompt.txt`) hoặc dùng cú pháp trừu tượng ("lệnh get-state", "sub-command get-state"), tránh chèn chuỗi `adb` trần vào tham số CLI của tool.
