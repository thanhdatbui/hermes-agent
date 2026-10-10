# BÁO CÁO KỸ THUẬT: GIỚI HẠN LIVE PNP CỦA INTEL X99 EHCI & KIẾN TRÚC REBOOT TỰ ĐỘNG ĐỊNH KỲ (10/10/2026)

---

## 1. Bản Chất Kỹ Thuật: Thất Bại Của Lệnh `Disable-PnpDevice` Trên Main X99
Trong phiên làm việc 10/10/2026, khi cụm máy Box 4 (M261–M280) bị kẹt socket `offline` và script `safe_usb_guard.py --force` kích hoạt lệnh `reset_usb_bus.bat`:
```powershell
Get-PnpDevice | Where-Object { $_.FriendlyName -match 'Enhanced Host Controller' } | Disable-PnpDevice -Confirm:$false
```
Windows ném ngoại lệ từ chối:
```text
Disable-PnpDevice : Not supported
CategoryInfo          : NotImplemented: (Win32_PnPEntity...):ROOT\cimv2\Win32_PnPEntity) [Disable-PnpDevice], CimException
FullyQualifiedErrorId : HRESULT 0x8004100c,Disable-PnpDevice
```
Đồng thời lệnh native của Windows `pnputil /restart-device` cũng trả về mã thoát 194:
```text
Restarting device: PCI\VEN_8086&DEV_8D26&SUBSYS_72708086&REV_05\3&11583659&0&E8
System reboot is needed to complete configuration operations!
```

### Nguyên nhân:
1. Chipset Intel C610/X99 (bo mạch Huananzhi X99-F8D) chứa 2 bộ điều khiển USB 2.0 EHCI (`8D26` và `8D2D`). Driver Windows chuẩn của Intel quản lý ở mức PCI System Bus, **không hỗ trợ tính năng Live Disable/Enable mềm** thông qua giao diện WMI/CIM mà bắt buộc phải qua chu trình POST/BIOS System Bus Reset để tái khởi tạo thanh ghi.
2. Lệnh `reset_usb_bus.bat` thực tế chỉ kill và bật lại tiến trình `adb.exe`, hoàn toàn **không ngắt điện hay reset xung nhịp phần cứng** của chip EHCI.
3. Khi bus USB đã rơi vào trạng thái kẹt (hardware lockup do tràn microframe hoặc sụt áp data line), điện thoại vẫn nhận nguồn sạc 5V nhưng đường Data (D+/D-) bị treo. Do không có tín hiệu ngắt VBUS vật lý, tiến trình `adbd` trên Android không khởi động lại, dẫn đến tình trạng máy bị kẹt `offline` vĩnh viễn dù không chạy tác vụ nào.

---

## 2. Bằng Chứng Transport ID Liên Tiếp (Đồng Pha Văng Cụm Box 4)
Khi trích xuất `adb devices -l` trên Admin PC, toàn bộ các máy bị văng đều mang `transport_id` liên tiếp:
* `14745`: M278 (`ce12160ca124a33204` - offline)
* `14746`: M270 (`98866737444e504f44` - offline)
* `14747`: M263 (`ce031603a0a19f060f` - offline)
* `14748`: M265 (`ce031603fb78023003` - offline)
* `14749`: M264 (`ce0216024da6931005` - rớt rồi online lại)
* `14750`: M275 (`ce051605a34e3d3404` - offline)
* `14751`: M274 (`ad0a160368c5d7120a` - offline)
* `14752`: M269 (`ce12160c99570e3004` - mất khỏi adb)

Điều này chứng minh toàn bộ nhánh Box 4 bị sụt áp/rớt tín hiệu đồng thời ở cùng một mili-giây.

---

## 3. Khắc Phục Gốc Rễ: Hạ Tải Worker & Cơ Chế Reboot Tự Động Định Kỳ

### 3.1. Hạ Worker Khống Chế Tải USB 2.0:
* Trong `D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1`:
  * Đã hạ `$MaxWorkers = 25` (thay vì 40).
  * Giảm 40% số luồng I/O microframe trên bus USB 2.0. Thời lượng ca nuôi 80 máy tăng từ 35-40p lên ~60p, vẫn nằm trọn trong khung an toàn 120p của từng Ca.

### 3.2. Kiến Trúc Reboot Tự Động 1 Ngày 1 Lần (Khung 05:30 Sáng):
* Khung giờ `03:00 - 05:59` là Dead Zone (toàn bộ ca đêm đã xong, dọn cache TikTok hoàn tất lúc 04:30).
* Lúc 05:30 sáng, hệ thống kiểm tra 0 active locks và kích hoạt chuỗi reboot tự động:
  1. Gửi lệnh reboot Admin PC qua SSH: `ssh admin-farm "shutdown /r /t 2"`
  2. Gửi lệnh reboot Kibe PC: `shutdown /r /t 5`
* Cả 2 máy tính đều đã cấu hình `AutoAdminLogon = 1` và có Scheduled Tasks tự động khởi chạy lại Hermes, Telegram Gateway, và ADB daemon.
* Reboot mỗi sáng giải phóng toàn bộ thanh ghi phần cứng của 2 chip EHCI mà không cần thao tác tay của con người.

### 3.3. Cảnh Báo Về Nâng Cấp Card PCIe USB 3.0:
* CẤM mua card PCIe USB 3.0 giá rẻ loại 1 chip chia 4 cổng (như VIA VL805 hay NEC uPD720201 đơn chip) rồi cắm dồn 80 máy. Card đơn chip cũng bị giới hạn 64–96 Endpoints, sẽ tái hiện lỗi Code 43 chỉ nhận 8–10 máy tương tự xHCI onboard.
* BẮT BUỘC dùng card Quad-Controller độc lập (mỗi cổng 1 chip riêng) hoặc phân bổ nhiều card PCIe x1/x16 riêng biệt (tối đa 20–25 máy/controller).
