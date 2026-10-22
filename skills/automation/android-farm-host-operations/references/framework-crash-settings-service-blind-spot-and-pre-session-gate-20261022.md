# Android Framework Blind Spot (Can't find service: settings) & Pre-Session Gate Triage (2026-10-22)

> Ref: Sự cố Máy 213 báo "Mất kết nối Wi-Fi (AP)" tại Ca 2 Chiều (22/10/2026).

---

## 1. Hiện Tượng & Ảo Giác Phân Loại Watchdog
- **Báo cáo của Watchdog:** `M213: Mất kết nối Wi-Fi (AP)`.
- **Thực tế hiện trường O(1) qua `inspect_machine.py 213`:**
  - Máy vẫn có IP Wi-Fi từ DHCP (`192.168.110.87`).
  - Lệnh truy vấn proxy `settings get global http_proxy` trả về:
    `cmd: Can't find service: settings`
  - Current Focus: `None`.
- **Bản chất kỹ thuật:** Tiến trình cốt lõi `system_server` (hoặc `com.android.providers.settings`) bên trong Android Framework bị treo hoặc crash ngầm. `servicemanager` của Android không tìm thấy service `settings`.
- **Bẫy Watchdog (`classify_feed_failure`):** Khi script runner không đọc được proxy do framework chết, chuỗi lỗi kích hoạt các keyword liên quan đến network/proxy, dẫn đến watchdog phân loại nhầm thành "Mất kết nối Wi-Fi (AP)".

---

## 2. Nghịch Lý: "Tại Sao Lúc Vận Hành Không Tự Động Cứu?"

### A. Điểm Mù Của Pre-Session Gate Trước Ca Chạy (`pre_session_device_gate.py`)
- Hàm `probe_device(machine_id)` chỉ gọi:
  `adb -s <serial> get-state` (timeout 3.0s).
- **Cơ chế:** Daemon `adbd` là tiến trình C/native chạy độc lập ở tầng Linux kernel, không phụ thuộc vào Android Java Runtime (ART) hay `system_server`.
- **Hệ quả:** Ngay cả khi toàn bộ framework Android bị crash hoặc kẹt cứng ở màn hình đen, daemon `adbd` vẫn phản hồi và trả về `device`.
- Pre-Session Gate coi M213 là máy khỏe mạnh (`status: ready`), bỏ qua bước cứu hộ trước ca và cấp máy vào batch chạy thật.

### B. Kỷ Luật In-Flight Fail-Fast Trong Ca Nuôi
Khi runner bắt đầu thực thi trên M213 và vấp phải lỗi `Can't find service: settings`:
1. **In-Flight chỉ có soft reconnect:** Cơ chế tự cứu trong lúc chạy (`vpn_preflight.py`) chỉ được phép gọi `adb reconnect` (reset socket USB). Lệnh này hoàn toàn vô hiệu đối với lỗi crash framework.
2. **Cấm reboot S7 giữa ca chạy (Anti-Pattern):** Để cứu framework chết, bắt buộc phải reboot máy điện thoại (Level 2). Tuy nhiên, một chu kỳ reboot S7 mất **45–60 giây**. Nếu worker tự ý reboot điện thoại trong ca:
   - Gây nghẽn luồng worker (worker thread starvation).
   - Gây timeout dây chuyền cho các máy xếp hàng sau.
   - Tạo bão kết nối USB / DHCP làm sập các máy lân cận đang lướt video.
3. **Quyết định đúng đắn của runner:** Runner kích hoạt Fail-Fast, đánh dấu máy thất bại và ngắt ngay lập tức để chuyển worker sang phục vụ các máy khác.

---

## 3. Quy Trình Cứu Hộ Phân Tầng O(1) & Khắc Phục Triệt Để

### Cứu hộ tức thời:
- Chạy `python D:/Taadaa/tools/recover_stuck_s7.py -m <N>`:
  - Level 1 (Soft recovery: `am force-stop` + `keyevent 223` + ping `echo 1`): Thất bại vì shell không phản hồi đúng.
  - Level 2 (Bypass shell direct reboot): Bắn lệnh `reboot:` trực tiếp qua daemon ADB, né hoàn toàn shell đang treo. Thiết bị reboot và phục hồi `system_server` trong ~25–40s.
  - Hậu kiểm: Kiểm tra `inspect_machine.py <N>` xác nhận `settings` service đã sống lại, có IP Wi-Fi, Proxy và Launcher focus.

### Kiến trúc vá dứt điểm điểm mù Pre-Session Gate:
- Nâng cấp `probe_device(machine_id)` trong `pre_session_device_gate.py`:
  - Không chỉ dừng ở `adb get-state == 'device'`.
  - Bổ sung 1 probe nhẹ tầng framework: `adb shell "service check settings"` hoặc `adb shell echo 1` (timeout cứng 2.0s).
  - Nếu `get-state` xanh nhưng probe framework thất bại $\rightarrow$ Đánh dấu máy cần cứu hộ ngay TRƯỚC CA, tự động kích hoạt `recover_device()` (Level 2) trước khi phát lệnh nuôi batch.
