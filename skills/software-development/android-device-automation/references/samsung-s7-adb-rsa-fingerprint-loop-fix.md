# Samsung Galaxy S7 (ROM Farm) ADB RSA Fingerprint Dialog Loop: Root Cause & Triệt để

## Hai kịch bản phân biệt rõ ràng (Crucial Distinction)

Cần phân biệt rạch ròi 2 nguyên nhân kích hoạt hiện tượng này:
1. **Kịch bản A: Do Điện thoại tắt màn hình (Sleep điện thoại):** Cổng USB trên điện thoại suspend/renegotiate khi tắt màn.
2. **Kịch bản B: Do Máy tính PC điều khiển (Host PC) Sleep/Standby rồi Wake/Reconnect (Kibe sleep):** Điện thoại màn hình vẫn sáng hoặc tắt không sao, nhưng khi PC sleep/wake hoặc kết nối lại RDP/session thì popup RSA lại bung ra hàng loạt.

---

## 1. Kịch bản B: PC Điều khiển (Host PC) Sleep rồi Bật/Reconnect lại

### Cơ chế & Nguyên nhân gốc rễ
- **Windows ngắt nguồn USB Host Controller khi Sleep (S3 Standby / Selective Suspend):**
  Khi PC Windows sleep, hệ điều hành cắt điện hoặc đưa `USB Root Hub` và các `Generic USB Hub` (hub 10-20-40 cổng) vào trạng thái suspend. Toàn bộ 80 thiết bị USB bị ngắt vật lý đồng loạt.
- **Crash/Restart Socket ADB Server:**
  Khi PC thức dậy (wake up) hoặc user reconnect RDP, 80 kết nối socket ADB bị broken pipe / reset. Tiến trình `adb.exe` (chạy ngầm từ tool điều khiển như GemPhoneFarm/Xiaowei) bị crash hoặc bị tool tự restart lại daemon `adb server`.
- **Race Condition & Timeout Auth Token:**
  Một `adb server` mới vừa khởi động, cùng lúc 80 điện thoại gửi yêu cầu bắt tay `AUTH_TOKEN`. Kết hợp việc file `/data/misc/adb/adb_keys` trên điện thoại đã quá đầy (>5KB) và server vừa restart, quá trình bắt tay đối soát RSA giữa adb host và adbd client bị timeout -> Android tự động kích hoạt fallback an toàn: **Bung popup UsbDebuggingActivity hỏi lại người dùng**.

### Cách xử lý triệt để cho PC điều khiển (Host PC)
1. **Tắt hoàn toàn chế độ Sleep / Standby trên PC điều khiển farm (Chạy 24/7):**
   Mở terminal / cmd (Run as Administrator) chạy:
   ```cmd
   powercfg /change standby-timeout-ac 0
   powercfg /change hibernate-timeout-ac 0
   ```
   *(Chỉ cho phép tắt màn hình hiển thị của PC, tuyệt đối không cho máy tính rơi vào Sleep/Standby S3).*

2. **Tắt cơ chế ngắt điện USB Hub (USB Power Management):**
   - Mở **Device Manager** (`devmgmt.msc`).
   - Mở rộng nhánh **Universal Serial Bus controllers**.
   - Chuột phải vào từng mục **USB Root Hub (USB 3.0 / 2.0)** và các **Generic USB Hub** -> **Properties** -> Tab **Power Management**.
   - **Bỏ tích (Uncheck)** mục: *"Allow the computer to turn off this device to save power"* (Cho phép máy tính tắt thiết bị này để tiết kiệm pin) -> Bấm **OK**.

---

## 2. Kịch bản A: Do Điện thoại Sleep / Tắt màn hình

### Cơ chế & Nguyên nhân gốc rễ
1. **USB Bus Renegotiation khi Sleep/Wake:**
   - Trên các dòng Samsung S7 (SM-G930F/W8/K/L/S) chạy ROM Farm, khi màn hình tắt (`Display Power: state=OFF`), cổng USB bước vào trạng thái suspend hoặc renegotiate kết nối với tool điều khiển farm (Xiaowei, GemLogin...).
   - Khi wake up, thiết bị ngắt và thiết lập lại phiên ADB, kích hoạt một vòng lặp xác thực RSA handshake mới.

2. **File `/data/misc/adb/adb_keys` bị đầy hoặc tràn dung lượng (>5KB):**
   - Trên các máy farm cắm qua nhiều PC/tool theo thời gian, file `/data/misc/adb/adb_keys` tích tụ hàng chục public key cũ.
   - Khi ghi đè key mới, tiến trình `UsbDebuggingActivity` của Android gặp lỗi phân quyền hoặc không thể truncate/append hợp lệ -> **Ghi thất bại ngầm (Silent Fail)**. Key của session hiện tại không được lưu xuống chip nhớ Flash.

3. **Cơ chế bảo mật `ro.adb.secure=1` trên ROM stock/user:**
   - Khi `[ro.adb.secure]: [1]`, `adbd` bắt buộc phải đối soát public key client với danh sách trong `adb_keys`. Nếu key không đọc được hoặc không khớp, popup lập tức bị đẩy lên giao diện.

### Cách xử lý
- **Duy trì màn hình điện thoại luôn sáng khi cắm cáp:**
  ```bash
  adb shell settings put global stay_on_while_plugged_in 3
  adb shell settings put system screen_brightness 0
  ```
- **Reset danh sách ủy quyền (Revoke USB Debugging Authorizations):**
  Vào *Cài đặt cho người phát triển* -> Chọn *Thu hồi ủy quyền gỡ lỗi USB* -> Bấm OK -> Restart adb server.

---

## 3. Giải pháp vĩnh viễn cấp Kernel / ROM (Áp dụng cho cả 2 kịch bản)

Nếu máy S7 đã unlock bootloader / root hoặc chạy ROM tùy biến:
- **Tắt hoàn toàn cơ chế xác thực RSA trong build.prop / default.prop**:
  ```properties
  ro.adb.secure=0
  ro.debuggable=1
  ```
  Khi `ro.adb.secure=0`, Android tắt hoàn toàn cơ chế hỏi key RSA. Dù PC sleep, rút cáp cắm lại, adb server restart hay cắm sang bất kỳ máy tính nào khác, kết nối ADB luôn thông suốt và **vĩnh viễn không bao giờ xuất hiện popup xác thực**.
