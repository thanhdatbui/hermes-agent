# ADB RSA Popup vs Host Sleep & Screen Off Timeout Analysis

## 1. Hiện tượng & Bản chất
- **Popup RSA tái diễn sau khi PC Sleep/Wake**: Khi PC (Kibe) rơi vào trạng thái Sleep/Standby (S3) hoặc ngắt/nối lại phiên RDP, Windows có cơ chế tiết kiệm điện ngắt nguồn USB Root Hub (`MSPower_DeviceEnable`). Khi wake up, toàn bộ bus USB bị reset đồng loạt, làm ADB server bị văng và khởi động lại. Do farm có 80 máy cùng handshake lại đồng thời trong khi file `/data/misc/adb/adb_keys` bị nghẽn (phình to >5KB), daemon `adbd` trên S7 timeout và fallback hiển thị popup "Cho phép gỡ lỗi USB".
- **Khác biệt cốt lõi: PC Sleep vs Điện thoại tắt màn hình**:
  - Điện thoại tự tắt màn hình (Display Power: OFF / Dozing): Kết nối USB vẫn duy trì nếu cắm cáp, không làm mất kết nối ADB.
  - PC Sleep: Host controller ngắt điện toàn bộ USB Root Hub làm rớt kết nối vật lý.

## 2. Các giải pháp kỹ thuật

### A. Tầng Host Windows (PC Kibe / Farm Admin)
1. Tắt chế độ ngắt điện cổng USB Root Hub:
   ```powershell
   $target = Get-CimInstance MSPower_DeviceEnable -Namespace root\wmi | Where-Object { $_.InstanceName -like '*USB\ROOT_HUB*' }
   $target.Enable = $false
   Set-CimInstance -CimInstance $target
   ```
2. Cấu hình Windows không sleep khi cắm sạc (AC):
   ```cmd
   powercfg /change standby-timeout-ac 0
   powercfg /change hibernate-timeout-ac 0
   ```

### B. Tầng Thiết bị Android (Samsung Galaxy S7)
1. **ROM Stock**:
   - `ro.adb.secure=1` nằm trong `boot.img` ramdisk không sửa nóng được mà không can thiệp kernel/bootloader.
   - Thao tác "Thu hồi ủy quyền gỡ lỗi USB" (Revoke USB debugging authorizations) trong Cài đặt nhà phát triển sẽ dọn sạch file `/data/misc/adb/adb_keys` bị phình to để lưu lại key mới ổn định.
2. **ROM Mod Farm (Auto boot on charge + Auto ADB connect)**:
   - Mod `ro.adb.secure=0` trong `boot.img`: Bỏ qua hoàn toàn tầng RSA, cắm máy tính nào cũng tự nhận, factory reset thoải mái không bị hỏi lại.
   - Mod `/system/bin/lpm`: Cắm sạc tự bật nguồn.
   - **Độ trust TikTok & SafetyNet**: Nếu không cài app Root (`su`, Magisk), chỉ mod boot bypass ADB và lpm thì TikTok chạy trong user space hoàn toàn không phát hiện, trust 100% như ROM gốc.

### C. Lưu ý về màn hình S7 & Tool Xiaowei (Tiểu Vi)
- Khi Xiaowei kết nối lại hoặc PC thức dậy, tool có thể tự động đẩy lệnh giữ màn hình thức:
  `settings put system screen_off_timeout 2147483647` (Integer.MAX_VALUE ~ 24.8 ngày).
- Để đưa máy về tự tắt màn hình bình thường (tiết kiệm pin & chống nóng màn hình farm):
  `settings put system screen_off_timeout 60000` (1 phút) hoặc `30000` (30 giây).
- Đảm bảo `settings get global stay_on_while_plugged_in` giữ ở giá trị `0`.
