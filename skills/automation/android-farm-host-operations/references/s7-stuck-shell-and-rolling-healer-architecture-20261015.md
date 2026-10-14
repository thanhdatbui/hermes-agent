# S7 Stuck Shell Recovery & Rolling Healer Architecture (2026-10-15)

## 1. Bản Chất Kỹ Thuật: Kẹt Shell vs Kẹt Transport USB
- **Kẹt Shell do Process/Deadlock (VẪN REBOOT ĐƯỢC TỪ PC):**
  - Giao thức ADB phân tách độc lập giữa service `shell:...` (`/system/bin/sh`) và service `reboot:...` trực tiếp của daemon `adbd`.
  - Khi một lệnh shell bị treo (ví dụ `dumpsys window` bị nghẽn buffer, TikTok chiếm giữ thread), tiến trình shell con bị kẹt nhưng daemon `adbd` và socket USB vẫn sống.
  - Lệnh direct `adb -s <serial> reboot` gửi packet điều khiển cấp thấp thẳng vào `adbd` $\rightarrow$ gọi `property_set("sys.powerctl", "reboot")` và khởi động lại S7 thành công từ PC mà không cần shell.
- **Kẹt Transport / Đứt Socket Nhân Linux (TÊ LIỆT HOÀN TOÀN TỪ PC):**
  - Khi bus USB 2.0 EHCI bị nghẽn đệm hoặc microframe drop, đường ống `/dev/android_adb` trên kernel S7 bị đứt.
  - Thiết bị rơi vào `offline` hoặc mất hẳn khỏi `adb devices`.
  - Do nguồn VBUS 5V từ Box Phone vẫn nuôi chân sạc, Android không nhận được uevent ngắt kết nối nên `adbd` không tự restart. Lúc này cả shell lẫn reboot đều không gửi được dữ liệu.

## 2. Kiến Trúc Cứu Hộ Phân Tầng O(1) (`recover_stuck_s7.py`)
Quy trình 3 cấp độ cứu hộ tự động:
1. **Level 1 (Soft Recovery — Timeout 3.0s):**
   - Gửi lệnh nhị phân nhẹ: `am force-stop com.ss.android.ugc.trill` và `input keyevent 223` (KEYCODE_SLEEP).
   - Kiểm tra hậu điều kiện `pidof`. Nếu app tắt và máy phản hồi trong 3s $\rightarrow$ hoàn tất ngay mà không reboot.
2. **Level 2 (Bypass Shell Direct Reboot — Timeout 5.0s):**
   - Chỉ kích hoạt khi Level 1 timeout/kẹt.
   - Bắn trực tiếp packet daemon: `adb -s <serial> reboot`.
   - Chờ `wait_for_device_boot` (tối đa 60s) kiểm tra `wait-for-device` và `get-state == 'device'`.
3. **Level 3 (Transport Triage):**
   - Thử `adb -s <serial> reconnect` (hoặc `adb reconnect offline`).
   - Nếu vẫn không nhận $\rightarrow$ phân loại `failed_transport`, cô lập máy lỗi và giải phóng tiến trình ngay để chống nghẽn farm.

## 3. Quy Chuẩn Rolling Healer Cho Toàn Farm (`batch_recover_s7.py`)
- **CẤM TUYỆT ĐỐI reboot đồng loạt cả dàn S7:** Gây bão PnP tràn bộ đệm USB X99, sụt áp nguồn Box Hub và bão DHCP Wi-Fi.
- **Khóa trần I/O kép (Dual-Throttle Invariants):**
  1. `max_workers = 8`: Tối đa 8 luồng song song, giữ thông lượng I/O trong ngưỡng an toàn 35 MB/s của 2 chip EHCI.
  2. `reboot_semaphore = threading.Semaphore(2)`: Khóa cứng tối đa **2 máy được reboot cùng một thời điểm**. Máy thứ 3 cần reboot bắt buộc phải chờ 1 trong 2 máy trước boot xong mới được cấp vé.
- **Tự động bỏ qua slot trống vật lý:** Luôn loại trừ máy 255 trên cụm Admin.
- **Triệt tiêu nháy console:** Mọi lệnh subprocess trên Windows bắt buộc kèm `creationflags=subprocess.CREATE_NO_WINDOW`.
