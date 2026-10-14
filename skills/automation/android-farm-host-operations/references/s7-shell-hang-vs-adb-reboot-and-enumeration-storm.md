# S7 Shell Hang vs ADB Direct Reboot & Enumeration Storm Pitfalls

## 1. Tại Sao CẤM Reboot Đồng Loạt 80 Máy S7 Trước Ca Nuôi
- **Không giải quyết được nghẽn bus USB:**
  - Nút thắt cổ chai nằm 100% ở Host Controller PC (Intel X99 2 chip EHCI USB 2.0 `8D26`, `8D2D`), trần băng thông ~35–40 MB/s.
  - S7 không tích tụ trễ trên đường truyền USB PHY. Độ trễ là do hàng đợi buffer và hardware registers của PC bị kẹt. Reboot PC gửi System Bus Reset giải phóng thanh ghi, còn reboot S7 không tác động tới thanh ghi controller PC.
- **Hiểm họa khi reboot 80 máy S7 đồng loạt:**
  1. *Bão USB Enumeration Storm:* 80 máy cùng boot và nạp `adbd` trong 1–2 phút làm nghẽn bus PnP, rụng cả cụm hub (Box 3, Box 4 rụng 8–16 máy), rơi vào `offline`.
  2. *Bẫy Flapping cáp Micro-USB & Unauthorized:* Chân cáp Micro-USB cũ bị dão/oxy hóa sẽ chập chờn khi ngắt/nối lại VBUS/data, làm trượt RSA handshake, rơi vào `unauthorized`.
  3. *Thermal Throttling & Đơ giật 5–10 phút đầu:* Sau boot, Android 8 kích hoạt MediaScanner, Knox, dexopt ngốn 100% CPU Exynos 8890, máy nóng ran. Nếu vào ca nuôi ngay sẽ bị focus timeout và văng app nặng hơn máy đang chạy bình thường.
  4. *Bão DHCP & Sập tiến trình nền:* 80 máy cùng xin cấp IP làm nghẽn Wi-Fi; xóa sạch `atx-agent` (7912), minicap, minitouch... bắt buộc phải init lại từ đầu.

## 2. Phân Biệt: Kẹt ADB Shell vs Kẹt USB Transport
- **Kẹt ở tầng App/Process Shell (`/system/bin/sh`):**
  - Trong giao thức ADB, `shell:...` và `reboot:...` là 2 service độc lập của daemon `adbd`.
  - Khi một tiến trình shell bị kẹt (deadlock, dumpsys treo, app đơ): `adb shell` bị timeout NHƯNG `adb -s <serial> reboot` VẪN HOẠT ĐỘNG vì packet reboot đi thẳng vào `adbd` gọi `property_set("sys.powerctl", "reboot")`.
- **Kẹt ở tầng USB Transport / Kernel / Socket PC:**
  - Khi pipe `/dev/android_adb` trên Linux kernel của S7 hoặc hàng đợi socket trên Windows bị đứt, máy chuyển sang `device offline` hoặc `device not found`.
  - Lúc này CẢ `adb shell` LẪN `adb reboot` ĐỀU KHÔNG GỬI ĐƯỢC.
  - Do nguồn 5V VBUS vẫn nuôi từ Box, điện thoại không biết cáp đã rớt nên không phát sinh uevent để restart `adbd`. Cách cứu từ PC: (1) `taskkill /F /IM adb.exe` restart adb server; (2) dùng nút reboot trên toolbar XiaoWei; (3) reboot Host PC để BIOS POST ngắt điện VBUS tạm thời kích hoạt lại uevent.

## 3. Kiến Trúc Cứu Hộ Phân Tầng O(1) Cho S7 (`recover_stuck_s7.py`)
- **Cấp 1 (Soft Recovery, timeout 3s):** Gửi lệnh shell nhẹ `am force-stop <pkg>` và `input keyevent 223` (sleep). Thành công -> phục hồi máy không cần reboot.
- **Cấp 2 (Bypass Shell Reboot, timeout 5s):** Nếu Cấp 1 timeout -> gọi trực tiếp `adb -s <serial> reboot` (service reboot) và chờ `wait-for-device` tối đa 60s.
- **Cấp 3 (Transport Triage):** Nếu Cấp 2 thất bại -> `adb reconnect` hoặc đánh dấu `BLOCKED` chờ mốc reboot PC định kỳ.
