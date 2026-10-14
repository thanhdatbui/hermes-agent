# S7 Reboot Anti-Pattern & Phân Biệt Kẹt ADB Shell vs USB Transport Stall

## 1. Bẫy Tư Duy: Có Nên Reboot S7 Trước Ca Nuôi Để Giảm Lag USB?
- **Khẳng định dứt khoát:** **TUYỆT ĐỐI KHÔNG NÊN reboot đồng loạt 80 máy S7 trước ca nuôi.**
- **Bản chất kỹ thuật nút thắt cổ chai:**
  * Nghẽn đường truyền USB nằm 100% ở **Host Controller PC** (2 chip Intel EHCI USB 2.0 `8D26`, `8D2D` trên bo mạch Huananzhi X99). Băng thông trần chỉ ~35–40 MB/s gánh 80 máy qua các hub chia tầng.
  * Chip USB PHY trên S7 chạy chuẩn cố định, không tích tụ rác hay nghẽn bộ đệm theo thời gian. Hiện tượng lag lệnh ADB là do hàng đợi buffer trên PC bị kẹt, không phải do chip S7 truyền chậm đi.
  * Reboot PC giải phóng được vì lệnh BIOS/UEFI gửi xung **PCI System Bus Reset** làm sạch thanh ghi phần cứng của controller trên mainboard. Reboot S7 hoàn toàn không có tác dụng này đối với bus USB của PC.

- **Hiểm họa nghiêm trọng khi reboot đồng loạt 80 máy S7:**
  1. **USB Enumeration Storm (Bão PnP):** 80 máy cùng boot và kích hoạt `adbd` trong 1–2 phút sẽ dội bão kết nối đồng thời lên chip EHCI của PC, gây sụt nguồn dữ liệu, văng cả cụm Hub (Box 3, Box 4) và kẹt máy ở `offline`.
  2. **Flapping chân cáp Micro-USB & Bẫy Unauthorized:** Cáp Micro-USB của dàn S7 (đời 2016) chân data (D+/D-) dão hoặc oxy hóa. Ngắt/nối lại kết nối đột ngột dễ gây chập chờn (flapping), socket 10061, hoặc rớt RSA key handshake khiến máy thành `unauthorized`.
  3. **Thermal Throttling & Giật lag 5–10 phút đầu:** Sau boot, Android 8 chạy hàng loạt background tasks nặng (MediaScanner, Google Play Services, dexopt, Knox), CPU Exynos/Snapdragon chạy 100% gây nóng máy và kích hoạt cơ chế bóp xung nhiệt độ. Mở TikTok ngay lúc này sẽ lag và văng app nặng hơn bình thường.
  4. **Bão sóng Wi-Fi & Xóa sạch daemon nền:** 80 máy cùng xin cấp IP làm nghẽn DHCP trên MikroTik/Aruba, đồng thời giết chết các daemon `atx-agent` (port 7912), minicap, minitouch... bắt buộc phải re-init tốn thời gian.

## 2. Phân Biệt: Kẹt ADB Shell vs Kẹt USB Transport / Hardware Socket
- **Câu hỏi:** "Khi máy S7 bị kẹt adb shell thì có reboot S7 từ PC được nữa không?"
- **Trả lời:** Phụ thuộc vào tầng bị kẹt (Shell Subsystem vs Transport Layer).

### Kịch bản A: Kẹt tầng tiến trình con / App deadlock (REBOOT ĐƯỢC TỪ PC)
- **Bản chất:** Giao thức ADB phân tách rõ ràng:
  * Service `shell:...` (mở terminal qua `/system/bin/sh`).
  * Service `reboot:...` (lệnh điều khiển nguồn độc lập xử lý trực tiếp bởi daemon `adbd`).
- **Hiện tượng:** Khi lệnh `adb shell dumpsys` bị treo, app TikTok bị deadlock hoặc script vướng vòng lặp: tiến trình shell bị kẹt nhưng socket USB và daemon `adbd` vẫn thông suốt.
- **Thực thi từ PC:** Gửi lệnh `adb -s <serial> reboot` vẫn đi thẳng vào daemon `adbd` $\rightarrow$ gọi `property_set("sys.powerctl", "reboot")` và S7 khởi động lại bình thường.

### Kịch bản B: Kẹt tầng USB Transport / Kernel Socket Pipe (TÊ LIỆT HOÀN TOÀN)
- **Bản chất:** Khi chip EHCI của PC bị nghẽn đệm hoặc đường ống `/dev/android_adb` trên kernel Linux của S7 bị đứt packet:
  * Máy báo `device offline` hoặc `device not found`.
  * Toàn bộ các service của ADB (cả `shell`, `reboot`, `push`, `pull`) đều không thể truyền byte dữ liệu nào.
- **Tử huyệt nguồn 5V VBUS:** Cáp sạc từ Box Farm vẫn cấp nguồn 5V liên tục. Do đó kernel Linux của S7 không nhận biết được sự cố ngắt kết nối (không sinh `uevent disconnect`) để tự restart lại `adbd`. Máy sẽ kẹt ở trạng thái "treo kết nối ảo" vĩnh viễn.

## 3. Quy Trình Cứu Hộ Từ PC Khi Mất Kết Nối Không Cần Bấm Tay
1. **Reset ADB Server trên Windows:**
   * `taskkill /F /IM adb.exe`
   * Gọi lại `adb devices` để kiểm tra xem lỗi có phải do buffer socket Windows `adb.exe` bị nghẽn hay không. Nếu phục hồi, lệnh `adb -s <serial> reboot` sẽ hoạt động.
2. **Kênh điều khiển native của XiaoWei (Tiểu Vi / Phóng Vệ):**
   * XiaoWei dùng driver stream riêng. Thử nút "Khởi động lại thiết bị" trên toolbar của XiaoWei để gửi control signal qua kênh stream.
3. **Reboot Host PC (Giải pháp triệt để nhất):**
   * Khi PC khởi động lại, trong 1–2 giây ở giai đoạn BIOS/UEFI POST, bo mạch chủ sẽ ngắt nguồn VBUS và gửi tín hiệu PCI bus reset.
   * Cú sụt áp này buộc S7 phát sinh uevent ngắt kết nối thật $\rightarrow$ khi Windows boot lên cấp lại nguồn, S7 tự động re-handshake và khởi động lại daemon `adbd` xanh tươi 100%.
