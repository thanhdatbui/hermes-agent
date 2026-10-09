# Kiến trúc USB Bus, Giới hạn Phần cứng & Khắc phục Văng Dàn Farm (ADB / XiaoWei)

## 1. Bản chất sự cố Văng Hàng Loạt Thiết Bị (USB Bus Collapse)
- **Sai lầm phổ biến:** Đổ lỗi cho Windows Power Plan (USB Selective Suspend / PCIe ASPM). Power saving chỉ can thiệp khi cổng USB IDLE (không có dữ liệu). Khi farm đang chạy hoặc bật XiaoWei/Jiwei, bus USB luôn có dữ liệu liên tục nên Power Plan không phải nguyên nhân gây rớt máy.
- **Nguyên nhân gốc rễ 1 - Nghẽn băng thông USB 2.0 (EHCI):**
  - Cổng USB 2.0 chỉ có băng thông thực tế ~35 - 40 MB/s chia chung cho toàn bộ controller.
  - Mỗi lệnh `adb exec-out screencap -p` trên Samsung S7 kéo về 1.5 - 2.5 MB ảnh PNG.
  - Khi 15 - 20 máy đồng loạt chụp màn hình / kéo XML UI / đẩy video cùng lúc, lưu lượng tức thời vượt trần băng thông USB 2.0 $\to$ Babble error / Port Reset Failed $\to$ Controller treo cứng.
- **Nguyên nhân gốc rễ 2 - Tràn Endpoint Contexts phần cứng (xHCI/EHCI Endpoint Exhaustion):**
  - Mỗi chip USB Controller chỉ hỗ trợ từ 64 đến 96 (tối đa 128) Endpoint Contexts.
  - 1 điện thoại Android gỡ lỗi USB chiếm từ 3 đến 5 endpoints (Control, Bulk IN/OUT cho ADB, MTP, Modem...).
  - 1 Controller phần cứng chỉ gánh an toàn tối đa 30 - 40 điện thoại. Cắm dồn 70 - 80 máy vào 1 controller bo mạch chủ chắc chắn gây tràn endpoint và rớt chập chờn.
- **Nguyên nhân gốc rễ 3 - Lệch pha Stagger (Phase Drift):**
  - Cấu hình `max_workers = 30-40` và stagger lúc khởi động (`build_machine_launch_plan` delay 2s - 8s) chỉ có tác dụng lúc bắt đầu ca.
  - Sau 5 - 15 phút xem video với thời lượng khác nhau (3s - 60s), tính so le bị phá vỡ. Xuất hiện các thời điểm ngẫu nhiên 10 - 20 worker cùng kết thúc và đồng loạt bắn lệnh `screencap`/`dump` trong cùng 1 giây.

---

## 2. Quy trình Cứu Nhanh Tại Chỗ (Fast USB Bounce < 5s - Không Restart PC)
Khi dàn máy bị văng trên ADB/XiaoWei, thanh ghi USB Controller bị treo cứng. Thay vì khởi động lại cả PC làm sập mọi tiến trình chạy nền, ép Windows reset controller và khởi động lại ADB:

```cmd
@echo off
:: C:\Taadaa_Service\reset_usb_bus.bat
echo [1/3] Killing ADB...
taskkill /F /IM adb.exe >nul 2>&1

echo [2/3] Bouncing USB Host Controllers...
powershell -Command "Get-PnpDevice | Where-Object { $_.FriendlyName -match 'Enhanced Host Controller' } | Disable-PnpDevice -Confirm:$false; Start-Sleep 2; Get-PnpDevice | Where-Object { $_.FriendlyName -match 'Enhanced Host Controller' } | Enable-PnpDevice -Confirm:$false"

echo [3/3] Restarting ADB server...
"C:\Program Files (x86)\xiaowei\tools\adb.exe" -a nodaemon server
```
*Tác dụng:* Reset toàn bộ bus USB 2.0 trong 2 giây, ADB và 80 máy tự động bắt tay lại ngay lập tức mà không ảnh hưởng tới tiến trình render/downloader/bot trên PC.

---

## 3. Kiến trúc Cắm Dây & BIOS Chuẩn Cho Farm (Bo Mạch Chủ Huananzhi X99-F8D)
1. **Bật USB 3.0 (xHCI) trong BIOS:**
   - Vào BIOS (`Delete` lúc boot) $\to$ `IntelRCSetup` (hoặc `Advanced`) $\to$ `South Bridge Configuration` $\to$ `USB Configuration`.
   - Bật: `XHCI Mode` = **Enabled**, `XHCI Pre-Boot Driver` = **Enabled**, `Route USB ports to XHCI` = **Enabled**.
   - Băng thông USB 3.0 đạt 5.000 Mbps (~500 MB/s, gấp >10 lần USB 2.0), khả năng cách ly lỗi cổng vượt trội.
2. **Cắm cáp vật lý phân tán:**
   - Rút cáp tổng của Hub khỏi cổng màu ĐEN (USB 2.0), cắm toàn bộ sang cổng màu XANH DƯƠNG (USB 3.0).
   - Phân tán đều các dây cáp tổng sang các cụm cổng khác nhau, không cắm dồn 4 dây vào 1 cặp cổng sát nhau.

---

## 4. Quy tắc Mở rộng Fleet Lớn (100 - 200 máy)
- **Quy tắc bất biến:** TUYỆT ĐỐI KHÔNG dùng 1 controller hay cắm dồn vào bo mạch chủ để gánh 100 - 200 máy.
- **Tiêu chuẩn công nghiệp:**
  - Trang bị **3 đến 4 Card PCIe USB 3.0 độc lập** (chip Renesas/NEC uPD720201 hoặc VIA VL805, 4 cổng riêng biệt).
  - Cắm nguồn phụ SATA / 4-pin Molex trực tiếp từ PSU máy tính vào từng card PCIe.
  - Mỗi card chỉ gánh tối đa 40 - 50 điện thoại (2-3 bộ Box Hub 16/20 cổng).
  - Cách ly hoàn toàn đường truyền và nguồn điện khỏi bo mạch chủ.

---

## 5. Lưu ý Vận hành Bot Hermes Gateway khi Host Reboot
- Khi PC controller (Kibe/Admin) reboot, tiến trình Gateway khởi động ở chế độ Cold Boot (`is_reconnect = False`).
- Telegram adapter mặc định kích hoạt cờ `drop_pending_updates = True` để dọn sạch hàng đợi server.
- **Hệ quả:** Mọi tin nhắn người dùng gửi qua Telegram trong lúc máy đang reboot (trước khi gateway connected) đều bị Telegram hủy bỏ và bot không bao giờ nhận được.
- Khi nghi ngờ bot không phản hồi sau reboot, cần kiểm tra log `logs/gateway.log` để xác nhận mốc thời gian connect.
