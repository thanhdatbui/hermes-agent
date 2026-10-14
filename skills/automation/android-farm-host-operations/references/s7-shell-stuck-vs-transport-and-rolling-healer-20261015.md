# Samsung S7 Stuck ADB Shell vs USB Transport & Rolling Healer Architecture (15/10/2026)

## 1. Bản Chất Kẹt Shell vs Kẹt Transport USB trên Samsung S7 (Android 8)
- **Kẹt Shell Subsystem (Level 1 Fail -> Level 2 Recoverable):**
  - Khi app (như TikTok) bị deadlock bộ nhớ, rò rỉ luồng hoặc tiến trình shell con bị treo:
  - Lệnh `adb shell ...` (`dumpsys window`, `am force-stop`, `input tap/keyevent`) bị treo cứng và timeout (>3s).
  - **Cơ chế cứu hộ:** Lệnh `adb -s <serial> reboot` **KHÔNG** đi qua shell `/system/bin/sh`. Giao thức ADB xử lý service `reboot:...` trực tiếp qua daemon `adbd`, gọi thẳng `property_set("sys.powerctl", "reboot")`. Vì vậy, khi shell bị kẹt nhưng transport USB còn sống, `adb reboot` từ PC vẫn khởi động lại S7 thành công 100%.
- **Kẹt USB Transport / Hardware Pipe (Level 3 Failed Transport):**
  - Khi controller EHCI USB 2.0 trên PC bị nghẽn buffer, microframe drop làm đứt pipe `/dev/android_adb` trên nhân Linux của S7.
  - Thiết bị rơi vào trạng thái `offline` hoặc biến mất khỏi `adb devices`.
  - **Tử huyệt VBUS 5V:** Do nguồn 5V từ Box Phone vẫn nuôi chân sạc, S7 tưởng cáp vẫn cắm nên không kích hoạt uevent để reset daemon `adbd`. Cả `adb shell` lẫn `adb reboot` đều tê liệt hoàn toàn. Chỉ cứu được bằng cách Reboot PC (ngắt VBUS trong BIOS POST 1–2s) hoặc lay/cắm lại cáp vật lý.

## 2. Quy Chuẩn Công Cụ Cứu Hộ Phân Tầng (`recover_stuck_s7.py`)
- **Level 1 (Soft Recovery):**
  - Pre-flight: `base_cmd + ["get-state"]`. Nếu != `'device'`, chuyển thẳng Level 3.
  - Soft action: `am force-stop com.ss.android.ugc.trill` và `input keyevent 223` (sleep màn hình).
  - Post-verify: Ping nhẹ `shell echo 1` (timeout 2.0s) để xác nhận shell đã phản hồi mượt mà.
- **Level 2 (Bypass Shell Direct Daemon Reboot):**
  - Khóa an toàn Cooldown: `~/.codex/device-locks/reboot_cooldown_<serial>.json` (ngưỡng 300s = 5 phút). Nếu vi phạm cooldown, hủy reboot (`aborted_cooldown`) để chống reboot loop trên farm.
  - Bắn lệnh `base_cmd + ["reboot"]` (timeout 5.0s), chờ `wait_for_device_boot` (tối đa 60s).
- **Level 3 (Transport Reconnect & Triage):**
  - Cú pháp chuẩn ADB: `base_cmd + ["reconnect"]`.
  - Nếu reconnect vẫn không nhận `device`, gắn nhãn `failed_transport` để cô lập, không để tiến trình treo làm nghẽn hàng đợi farm.

## 3. Kiến Trúc Rolling Healer Toàn Farm (`batch_recover_s7.py`)
- **Khống chế I/O Concurrency (`max_workers = 8`):** Chạy cuốn chiếu qua ThreadPoolExecutor tối đa 8 workers song song, an toàn với băng thông trần 35 MB/s của 2 chip EHCI USB 2.0.
- **Khóa Chống Bão Reboot (`reboot_sem = threading.Semaphore(2)`):** BẮT BUỘC kẹp trần tối đa 2 máy được reboot đồng thời trên toàn farm. Máy thứ 3 phải xếp hàng chờ máy trước boot xong mới được cấp vé reboot, triệt tiêu sụt áp nguồn Box Hub và bão DHCP Wi-Fi trên AP/MikroTik.
- **Tự động lọc slot trống:** Tự động bỏ qua máy 255 trên Admin Farm.
- **Chống cướp focus:** Mọi lệnh subprocess trên Windows bắt buộc có cờ `creationflags=subprocess.CREATE_NO_WINDOW`.
- **Thực nghiệm toàn farm (~160 máy):** Hoàn tất quét toàn bộ cả 2 cụm Kibe và Admin trong <33 giây, 155/159 máy (97.5%) xử lý ở Level 1 trong 1.5s/máy, không gây reboot thừa, cô lập chính xác các máy bị lỗi cáp vật lý (M10, M30, M228).
