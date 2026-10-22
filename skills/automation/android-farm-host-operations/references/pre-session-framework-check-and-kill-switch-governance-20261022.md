# Pre-Session Android Framework Responsiveness Check & Kill-Switch Governance (22/10/2026)

## 1. Hiện Tượng & Điểm Mù Hệ Thống
- **Hiện tượng (Sự cố Máy 213):**
  * Watchdog báo cáo Máy 213 thất bại với lý do `"Mất kết nối Wi-Fi (AP)"`.
  * Thực tế khảo sát qua `inspect_machine.py 213`: Máy vẫn có IP Wi-Fi (`192.168.110.87`), nhưng khi đọc proxy thì Android văng lỗi `cmd: Can't find service: settings`.
  * Runner không đọc được proxy nên phân loại nhầm thành mất kết nối Wi-Fi.
- **Điểm mù Pre-Session Gate:**
  * `pre_session_device_gate.py` trước đây chỉ chạy `adb get-state` (thăm dò tầng Linux kernel daemon `adbd`).
  * Khi `system_server` của Android bị treo hoặc crash service `settings`, `adbd` vẫn phản hồi và trả về `device` (máy xanh).
  * Gate bị đánh lừa là máy khỏe mạnh (`ready`), giao việc cho runner nuôi acc.
- **Tại sao Runner Trong Ca Không Cứu (In-Flight Fail-Fast Invariant):**
  * In-flight self-healing (`vpn_preflight.py`) chỉ chạy `adb reconnect` (reset socket USB). Soft reconnect không thể hồi sinh `system_server` của Android.
  * Muốn hồi sinh `settings` bắt buộc phải reboot điện thoại (Level 2).
  * Trong ca nuôi, reboot 1 máy S7 mất 45–60 giây. Nếu worker tự ý reboot sẽ làm treo thread, timeout dây chuyền và vi phạm nghiêm ngặt quy tắc an toàn farm: **CẤM reboot S7 trong ca nuôi**. Runner buộc phải fail-fast ngắt máy lỗi để bảo vệ các máy khác.

## 2. Giải Pháp Chuẩn Hóa 2 Tầng (`pre_session_device_gate.py`)
1. **Kiểm tra 2 Tầng (Kernel + Framework):**
   - Tầng 1: `adb get-state` (timeout 3.0s) xác nhận daemon `adbd` online.
   - Tầng 2: `adb shell service check settings` (timeout 2.0s).
2. **Siết Điều Kiện Thành Công Chống False-Positive:**
   - Bắt buộc `returncode == 0`, `stdout` không rỗng, chứa chuỗi `"found"` (case-insensitive) và **TUYỆT ĐỐI KHÔNG CHỨA** `"not found"`.
   - Nếu `returncode != 0`: báo lỗi chuẩn định dạng `exit_code_{rc}` thay vì nuốt stderr.
3. **Kill-Switch Bảo Trợ Rollback Tức Thời:**
   - Biến môi trường: `FRAMEWORK_CHECK_ENABLED` (mặc định `'1'`).
   - Nếu `FRAMEWORK_CHECK_ENABLED='0'`: Gate tự động bỏ qua Tầng 2 và chấp nhận kết quả `get-state` của Tầng 1, cho phép rollback tức thời 0-code nếu phát sinh false-negative diện rộng.
4. **Structured Telemetry & Quan Sát:**
   - Ghi nhận `emit_telemetry("framework_check", {"serial": ..., "machine_id": ..., "status": "success"|"failure"|"timeout"|"error", "latency_sec": ...})`.
5. **Test Suite Hoàn Hảo (66 tests passing):**
   - Bao phủ các nhánh: success local/remote, framework timeout, parametrize các chuỗi phản hồi bất thường (`not found`, `cmd: Can't find service`, chuỗi ngẫu nhiên, stdout rỗng, returncode != 0), và kiểm thử kill-switch disabled.
