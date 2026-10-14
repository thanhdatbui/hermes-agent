# Phân Tầng Cứu Hộ S7 Khi Kẹt Shell & Quy Tắc Cấm Reboot Đồng Loạt Cả Dàn (15/10/2026)

## 1. Bản Chất Kỹ Thuật: Reboot PC vs Reboot S7 Đối Với Nghẽn USB Bus
- **Nút thắt cổ chai nằm 100% ở Host Controller PC (Intel X99 EHCI USB 2.0):**
  * Dàn 80 máy cắm dồn vào 2 chip EHCI (`8D26`, `8D2D`), băng thông trần 35–40 MB/s. Khi chạy dồn dập nhiều giờ, thanh ghi phần cứng và buffer queue của chip EHCI trên bo mạch chủ bị nghẽn (lỗi phần cứng `HRESULT 0x8004100c`, Windows không reset mềm được).
  * **Reboot PC** kích hoạt xung PCI System Bus Reset từ BIOS/UEFI, xả sạch điện và thanh ghi phần cứng của 2 chip USB trên mainboard, giải phóng 100% băng thông và socket ADB.
- **S7 không gây tích tụ độ trễ trên đường truyền USB:**
  * Chip điều khiển USB PHY trên Samsung S7 (Android 8) chạy chuẩn phần cứng cố định, không "tích tụ rác" trong đường truyền USB.
  * Hiện tượng "lag truyền dữ liệu" (lệnh shell delay >10s, dumpsys timeout) là do hàng đợi buffer trên PC bị nghẽn, không phải chip S7 truyền chậm đi.

## 2. Hiểm Họa Nghiêm Trọng Nếu Reboot Đồng Loạt 80 Máy S7 (CẤM BATCH REBOOT)
1. **Bão PnP & Tràn bộ đệm USB PC (USB Enumeration Storm):**
   * Khi 80 máy S7 cùng khởi động lại, trong 1–2 phút sau boot, 80 tiến trình `adbd` đồng loạt gửi tín hiệu kết nối USB về PC.
   * Cú sốc I/O này làm quá tải chip EHCI ngay lập tức, dẫn tới rụng cả cụm Hub (Box 3, Box 4 rụng 8–16 máy) và kẹt trạng thái `offline` hoặc biến mất khỏi `adb devices`.
2. **Bão Sụt Áp Nguồn & Flapping Chân Cáp Micro-USB:**
   * S7 boot ngốn dòng điện tối đa (CPU 100% + sạc nhanh), gây sụt áp nguồn VBUS trên các Box Hub 20 cổng.
   * Chân cắm Micro-USB dão/oxy hóa sẽ bị flapping (nhấp nháy online/offline), socket error 10061, hoặc rớt RSA Handshake thành `unauthorized`.
3. **S7 Bị Giật Lag & Thermal Throttling Sau Boot:**
   * Android 8 kích hoạt MediaScanner, Knox, Play Services, dexopt ngầm trong 5–10 phút đầu sau boot. CPU Exynos 8890 chạm trần 100%, máy nóng ran, kích hoạt giảm xung nhiệt. Đẩy ca nuôi vào lúc này sẽ làm TikTok giật lag, văng app và timeout `failed to focus` nặng nề hơn.
4. **Bão Sóng Wi-Fi & Sập Service Nền:**
   * 80 máy cùng DHCP hammer lên MikroTik / Aruba AP, tăng nguy cơ rớt kết nối Proxy và trôi sang Rogue SSID.
   * Toàn bộ daemon automation nền như `atx-agent` (port 7912), minicap, minitouch bị xóa sạch, phải tốn công init lại.

## 3. Kiến Trúc Cứu Hộ Phân Tầng O(1) (`recover_stuck_s7.py`)
Khi một máy bị đơ màn hình hoặc lệnh shell bị treo, áp dụng cơ chế 3 cấp độ cứu hộ tăng dần:
- **Cấp 1 — Cắt ngọn (Soft recovery, timeout 3.0s):**
  * Gửi lệnh nhị phân nhẹ: `am force-stop com.ss.android.ugc.trill` và `input keyevent 223` (tắt màn hình, chống nóng).
  * Nếu hoàn thành trong <= 3s $\rightarrow$ máy được cứu sống ngay trong 1.5s mà KHÔNG cần reboot.
- **Cấp 2 — Đột phá ADB Reboot (Bypass shell, timeout 5.0s):**
  * Bản chất: Lệnh `adb reboot` KHÔNG đi qua hệ thống shell (`/system/bin/sh`). Service `reboot:` được quản lý trực tiếp bởi daemon `adbd`.
  * Khi tiến trình shell con bị kẹt deadlock nhưng daemon `adbd` còn sống $\rightarrow$ bắn trực tiếp `adb -s <serial> reboot` sẽ ép máy khởi động lại ngay.
  * Sau đó gọi `wait_for_device_boot` (dùng `adb wait-for-device` và kiểm tra `get-state == 'device'`, timeout 60s).
- **Cấp 3 — Phân tầng Socket/Transport (Fail-Fast Triage):**
  * Nếu lệnh reboot cũng thất bại (do đứt socket pipe `/dev/android_adb` hoặc rớt cáp vật lý) $\rightarrow$ thử `reconnect <serial>`.
  * Nếu vẫn unresponsive $\rightarrow$ đánh dấu ngay `failed_transport`, thoát ngay lập tức để không làm treo batch runner.

## 4. Quy Tắc Triển Khai Toàn Farm
- **Cứu hộ cá biệt (O(1)):** Gọi `python D:/Taadaa/tools/recover_stuck_s7.py --machine <N>` khi phát hiện máy lỗi.
- **Chống bão reboot:** Runner hoặc Healer quét toàn farm BẮT BUỘC khống chế tối đa không quá 1–2 máy reboot cùng lúc, ưu tiên Cấp 1 dọn app trước.
