# USB Bus Capacity, Fast Hardware Bounce & Endpoint Scaling (Taadaa Phone Farm)

## 1. Bản Chất Sự Cố "Văng Hàng Loạt Máy Trong ADB / XiaoWei"
- **Sai lầm phổ biến:** Đổ lỗi cho Windows Power Plan (USB Selective Suspend / PCIe ASPM). Power saving chỉ can thiệp khi cổng USB IDLE (không có dữ liệu). Khi farm đang chạy hoặc bật XiaoWei/Jiwei, bus USB luôn có dữ liệu liên tục nên Power Plan không phải nguyên nhân gây rớt máy.
- **Nghịch lý "Đã giới hạn max_workers = 30-40 và có Stagger tại sao vẫn sập?":**
  1. **Hiện tượng Lệch Pha (Phase Drift / Stagger Erosion):**
     - Code `build_machine_launch_plan` chỉ áp dụng stagger delay (2s - 8s) ở đúng thời điểm ban đầu khi worker khởi động.
     - Trong quá trình nuôi acc, thời lượng video trên TikTok là biến thiên ngẫu nhiên (video ngắn 3-5s, video vừa 15-30s, video dài 60s).
     - Sau 5 - 15 phút, tính so le ban đầu bị xóa sạch (phase drift). Sẽ xuất hiện các thời điểm ngẫu nhiên mà 10 - 20 worker trong số 40 worker cùng kết thúc xem video và đồng loạt gọi lệnh chụp màn hình (`screencap`) hoặc `dump uiautomator` trong cùng 1 giây.
  2. **Vượt Trần Băng Thông USB 2.0 (EHCI):**
     - Bo mạch chủ Huananzhi X99-F8D bị disable chip Intel USB 3.0 (`8D31`) trong BIOS $\to$ toàn bộ 80 máy dồn vào 2 chip USB 2.0 (EHCI `8D26/8D2D`).
     - Băng thông thực tế của 1 Controller USB 2.0 chỉ là ~35 - 40 MB/s chia sẻ cho toàn bộ các cổng.
     - Mỗi file ảnh PNG 1080p từ `screencap -p` nặng khoảng 1.5 - 2.5 MB.
     - Khi 15 worker đồng loạt chụp ảnh trong 1 giây: $15 \times 2\text{ MB} = \mathbf{30\text{ MB/s}}$ $\to$ Chiếm trọn 100% băng thông USB 2.0.
     - Chip controller bị quá tải ngắt phần cứng (Hardware Interrupt Overload), sinh lỗi `Babble error` / `Port Reset Failed` $\to$ Windows ngắt điện cổng hub $\to$ rớt hàng loạt thiết bị.

---

## 2. Quy Trình Cứu Nhanh Tại Chỗ (Fast USB Bounce < 5s - Không Restart PC)
Khi thanh ghi của chip USB Controller bị treo (Halted/Babble), `adb kill-server` vô tác dụng vì lỗi nằm ở tầng phần cứng. Nhưng thay vì khởi động lại cả PC làm sập mọi tiến trình nền (render, downloader, bot), ta ép Windows reset đúng 2 chip USB Host Controller:

Tạo script `C:\Taadaa_Service\reset_usb_bus.bat` (chạy Run as Administrator):
```cmd
@echo off
echo [1/3] Dang kill ADB server...
taskkill /F /IM adb.exe >nul 2>&1

echo [2/3] Dang reset chip USB Host Controller tren bo mach chu...
powershell -NoProfile -Command "Get-PnpDevice | Where-Object { $_.FriendlyName -match 'Enhanced Host Controller' } | Disable-PnpDevice -Confirm:$false; Start-Sleep 2; Get-PnpDevice | Where-Object { $_.FriendlyName -match 'Enhanced Host Controller' } | Enable-PnpDevice -Confirm:$false"

echo [3/3] Dang khoi dong lai ADB server...
"C:\Program Files (x86)\xiaowei\tools\adb.exe" -a nodaemon server
```
- **Tác dụng:** Cắt điện và cấp lại xung nhịp cho toàn bộ bus USB 2.0 trong 2 giây. Toàn bộ 80 máy sẽ tự động bắt tay lại với ADB ngay lập tức mà không cần reboot máy tính.

---

## 3. Quy Tắc Phần Cứng & Mở Rộng Fleet (Scaling 100 - 200 Máy)
- **1 Card PCIe USB 3.0 có cân được 200 máy không?**
  - **TUYỆT ĐỐI KHÔNG.** Giới hạn phần cứng của chip USB Controller (Renesas uPD720201, VIA VL805 hay ASMedia) là số lượng **USB Endpoint Contexts** (tối đa chỉ 64 - 96, hiếm khi tới 128 contexts/chip).
  - 1 điện thoại Samsung S7 bật gỡ lỗi USB chiếm từ 3 đến 5 endpoints (ADB, MTP, Modem, Control).
  - 1 chip controller chỉ gánh tối đa an toàn khoảng **30 - 40 điện thoại**. Cắm quá con số này sẽ dính lỗi phần cứng `Not enough USB controller resources`.
- **Kiến trúc chuẩn cho dàn 200 máy trên bo mạch Huananzhi X99-F8D:**
  - Main X99-F8D Dual Xeon có 3 khe PCIe x16 và các khe PCIe x1.
  - Cần cắm **3 đến 4 Card PCIe USB 3.0 độc lập** (mỗi card dùng 1 chip riêng, có cổng cấp nguồn phụ SATA/Molex trực tiếp từ PSU).
  - Mỗi card cắm 2-3 bộ Box Hub (tối đa 40 - 50 máy/card).
  - 200 máy sẽ được phân bổ đều trên 4 làn bus PCIe độc lập, cách ly hoàn toàn khỏi bo mạch chủ.

---

## 4. Hành Vi Hermes Gateway Khi Host Reboot (Mất Tin Nhắn Telegram)
- Khi PC Controller (Kibe/Admin) reboot, tiến trình Gateway khởi động lại ở chế độ **Cold Boot** (`is_reconnect = False`).
- Trong adapter Telegram (`plugins/platforms/telegram/adapter.py`):
  ```python
  polling_started = await self._start_polling_resilient(
      drop_pending_updates=not is_reconnect,  # Cold boot -> drop_pending_updates = True
      error_callback=_polling_error_callback,
  )
  ```
- **Hệ quả vận hành:** Cờ `drop_pending_updates=True` ra lệnh cho Telegram server **xóa sạch (purge) toàn bộ hàng đợi tin nhắn** được gửi tới bot trong lúc PC đang tắt/reboot.
- Khi nghi ngờ bot bỏ lỡ chỉ đạo của User sau sự cố reboot, đối soát log `logs/gateway.log` mốc thời gian `Connected to Telegram` để biết chính xác các tin nhắn nào đã bị Telegram xóa.
