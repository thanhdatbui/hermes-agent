# S7 Tiered Recovery & Rolling Healer Architecture (2026-10-15)

## 1. Bối Cảnh & Vấn Đề
Khi vận hành Phone Farm 160 máy Samsung S7 (Android 8) trên host mainboard Huananzhi X99 Dual Xeon kết nối qua cổng USB 2.0 EHCI:
- **Câu hỏi phổ biến từ Operator:** "Host PC bị nghẽn bus USB phải reboot trước ca nuôi để xả thanh ghi. Vậy có nên thêm bước reboot 80 máy S7 trước ca nuôi để giảm lag truyền USB không?"
- **Kết luận kiến trúc:** **TUYỆT ĐỐI KHÔNG REBOOT S7 ĐỒNG LOẠT TRƯỚC CA.**
  1. *Nghẽn bus nằm ở Host Controller PC:* Trần USB 2.0 EHCI chỉ 35–40 MB/s và kẹt thanh ghi phần cứng bo mạch chủ X99 (lỗi `0x8004100c`). S7 không tích tụ rác ở controller USB.
  2. *Reboot đồng loạt 80 máy S7 gây thảm họa:*
     - Bão USB Enumeration Storm làm sập toàn bộ Hub (Box 3, Box 4 rụng 8–16 máy).
     - Rung lắc/flapping chân micro-USB làm văng RSA handshake rơi vào `unauthorized`.
     - Android 8 sau boot chạy MediaScanner, Knox, Play Services làm CPU 100%, nóng ran và thermal throttling trong 5–10 phút đầu.
     - Bão kết nối DHCP làm nghẽn router MikroTik / Aruba AP.

## 2. Bản Chất Lệnh Shell Kẹt vs Reboot Từ PC
Khi máy S7 bị đơ/kẹt lệnh shell:
- **Kẹt ở tầng App / Process (Vẫn reboot được từ PC):**
  - Giao thức ADB tách biệt service `shell:...` (`/system/bin/sh`) và service `reboot:...` (daemon `adbd`).
  - Lệnh `adb -s <serial> reboot` gửi packet trực tiếp tới `adbd` -> gọi `property_set("sys.powerctl", "reboot")` bỏ qua hoàn toàn shell đang treo.
- **Kẹt ở tầng USB Transport / Kernel (Tê liệt hoàn toàn):**
  - Đứt socket pipe `/dev/android_adb` trên nhân Linux của S7 do bus USB 2.0 rớt vi khung.
  - Máy rơi vào `device offline` hoặc `device not found`. Cả `adb shell` lẫn `adb reboot` đều không gửi được byte nào.
  - Chân sạc 5V VBUS vẫn nuôi điện thoại nên Linux không kích hoạt uevent nhận cáp để restart `adbd`. Trường hợp này chỉ cứu được bằng cách cắm lại cáp hoặc reboot Host PC để xả nguồn VBUS 1-2s trong BIOS POST.

## 3. Kiến Trúc 3 Cấp Cứu Hộ O(1) (`recover_stuck_s7.py`)
Triển khai công cụ `D:/Taadaa/tools/recover_stuck_s7.py`:
- **Cấp 0 (Pre-flight State Check):**
  - Gọi `adb -s <serial> get-state` trước khi can thiệp.
  - Nếu trạng thái != `device` (offline, unauthorized, missing) -> chuyển ngay xuống Cấp 3 Reconnect/Triage, TUYỆT ĐỐI KHÔNG reboot mù khi thiết bị chưa sẵn sàng.
- **Cấp 1 (Soft Recovery — Dọn App & Sleep):**
  - Timeout 3.0s: `am force-stop com.ss.android.ugc.trill` và `input keyevent 223` (KEYCODE_SLEEP).
  - *Post-condition verify:* Ping nhẹ `shell echo 1` (timeout 2.0s) để xác nhận shell thực sự thông suốt. Hoàn tất trong 1.5s/máy, không cần reboot.
- **Cấp 2 (Bypass Shell Reboot & Cooldown Guard):**
  - Chỉ kích hoạt khi Cấp 1 timeout do shell deadlock.
  - Gửi lệnh `adb -s <serial> reboot` (timeout 5.0s, đi tắt qua daemon).
  - *Chống Reboot Loop (Cooldown Guard):* Kiểm tra lock file `~/.codex/device-locks/reboot_cooldown_<serial>.json`. Nếu máy vừa reboot trong vòng 5 phút (300s) -> lập tức ABORT (`aborted_cooldown`) để bảo vệ nguồn điện Box và flash memory của S7.
  - Chờ máy boot lại bằng `wait-for-device` và kiểm tra `get-state == 'device'`.
- **Cấp 3 (Transport Reconnect & Triage):**
  - Cú pháp chuẩn ADB: `base_cmd + ["reconnect"]` (không dùng `reconnect <serial>` sai cú pháp).
  - Nếu thiết bị vẫn im lặng sau reconnect -> gắn cờ `failed_transport` và dừng ngay.
- **Telemetry có cấu trúc:**
  - Xuất format `[TELEMETRY_METRIC] {"event": "device_recovery", "level": N, "latency_sec": X.X, ...}` để ingest và theo dõi.
- **Chống cướp focus:** Mọi lệnh subprocess trên Windows đều dùng `creationflags=subprocess.CREATE_NO_WINDOW (0x08000000)`.

## 4. Cơ Chế Rolling Healer Toàn Farm (`batch_recover_s7.py`)
Khi cần quét dọn, hạ nhiệt và đưa toàn bộ dàn S7 về sleep trước ca nuôi:
- **CẤM:** Quét 80-160 máy một lúc (gây nghẽn bus USB 2.0).
- **Cơ chế Throttle kép đã nghiệm thu:**
  1. `ThreadPoolExecutor(max_workers=8)`: Giới hạn tối đa 8 luồng song song, tương thích với Heavy-IO Gate của Farm.
  2. `reboot_sem = threading.Semaphore(2)`: Nếu có nhiều máy cùng bị kẹt shell cần reboot, tối đa CHỈ ĐÚNG 2 MÁY được reboot cùng một thời điểm. Máy thứ 3 phải xếp hàng chờ máy trước boot xong mới được cấp vé reboot.
- **Tự động lọc slot trống:** Tự động bỏ qua máy 255 trên Admin Farm.
- **Hiệu năng thực tế kiểm chứng (15/10/2026):**
  - Quét sạch 159 máy vật lý trên cả 2 cụm (Kibe 1-80 và Admin 201-280) chỉ trong **33 giây**.
  - 155/159 máy (97.5%) xử lý thành công ở Cấp 1 trong 1.5s/máy, 0 máy bị reboot oan.
  - Phát hiện chính xác 3 máy đứt chân data cáp Micro-USB vật lý (M10, M30 Kibe và M228 Admin).
