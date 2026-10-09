# Xử lý sự cố ngắt kết nối Xiaowei (放卫) & Kẹt Socket ADB Transport Deadlock

## 1. Hiện tượng & Triệu chứng nhận diện
- **Trên giao diện Xiaowei (放卫安卓投屏):** Ô slot thiết bị hiển thị biểu tượng điện thoại màu cam cùng thông báo *"Phone disconnected, please check"*.
- **Trên ADB Server:**
  - *Dạng 1 (ADB Socket Hang/Deadlock):* Máy vẫn có tên trong `adb devices` với trạng thái `device`, nhưng bất kỳ lệnh `adb shell` nào cũng bị treo vĩnh viễn (timeout >10s).
  - *Dạng 2 (Màn hình ngủ / Rớt stream video):* Lệnh ADB shell vẫn phản hồi bình thường, nhưng Xiaowei vẫn báo cam mất kết nối.
  - *Dạng 3 (Mất kết nối phần cứng):* Máy biến mất hoàn toàn khỏi danh sách `adb devices`.

---

## 2. Phân tích nguyên nhân gốc rễ (Root Cause Analysis)

### a. Kẹt socket tầng Transport (`adbd` Deadlock trên Android 8.0 / Samsung S7)
- Dàn máy farm sử dụng Samsung Galaxy S7 (Android 8.0). `adbd` trên máy chỉ có 1 kênh USB vật lý nhưng phải gánh đồng thời:
  1. Luồng video H.264 liên tục của Xiaowei qua `XWCaptureScreen.jar` (chiếm dụng băng thông lớn).
  2. Bão lệnh shell đa luồng từ các cronjob/watchdog tự động quét định kỳ qua mạng LAN.
- Khi hub USB bị nghẽn buffer hoặc drop packet, `adbd` trên điện thoại rơi vào deadlock chờ khóa futex (`futex_wait_queue_me` / half-closed socket). Phía máy tính, ADB daemon giữ socket treo và không tự giải phóng, khiến mọi lệnh shell tiếp theo vào serial đó bị nghẽn hoàn toàn (`TIMEOUT_HUNG`).

### b. Ngừng render màn hình khi máy đi vào Sleep/Dozing
- Xiaowei thu hình bằng cách hook vào Android Surface Display thông qua `XWCaptureScreen.jar`.
- Khi máy rảnh và tắt màn hình (do watchdog đặt `stay_on_while_plugged_in = 0` hoặc hết timeout màn hình), Android GPU ngắt render khung hình để tiết kiệm điện. Tốc độ khung hình (FPS) rớt về 0 ➔ Xiaowei nhận định mất tín hiệu video và chuyển sang biểu tượng ngắt kết nối màu cam.

### c. Phân biệt ngắt kết nối vật lý bằng Windows PnP (Device Manager)
Khi máy biến mất khỏi `adb devices`, kiểm tra trạng thái bus USB trên máy host (Admin/Kibe) qua PowerShell:
```powershell
Get-PnpDevice | Where-Object { $_.InstanceId -like "*<serial>*" } | Select-Object FriendlyName, Status, Present, Problem
```
- Nếu trả về: `Present: False` kèm `Problem: CM_PROB_PHANTOM` (Error code 45) ➔ Cáp USB bị lỏng, tuột khỏi Hub hoặc điện thoại bị sập nguồn / hỏng phần cứng.

---

## 3. Quy trình cứu hộ & khắc phục dứt điểm (Remediation Protocol)

### Bước 1: Bẻ gãy Deadlock socket bằng `adb reconnect` (Không cần rút cắm cáp tay)
Không cần thao tác vật lý. Gửi lệnh tái lập handshake USB từ host:
```bash
adb -s <serial> reconnect
# Đối với cụm Admin Remote:
adb -H 192.168.110.119 -P 5037 -s <serial> reconnect
```
Lệnh này ép ADB server đóng pipe bị nghẽn và renegotiate lại USB transport trên điện thoại trong < 1.5 giây. Thiết bị sẽ ngay lập tức phản hồi lại shell.

### Bước 2: Đánh thức Surface Display phục hồi luồng Xiaowei
Sau khi socket sống lại, gửi keyevent đánh thức màn hình để GPU kích hoạt lại pipeline video:
```bash
adb -s <serial> shell input keyevent 224
```
Xiaowei sẽ tự động nhận diện lại frame buffer và khôi phục màn hình stream bình thường.

### Bước 3: Cấu hình chống ngủ & chống ám màn AMOLED
Để Xiaowei hoạt động liên tục 24/7 mà không làm cháy bóng/ám màn trên tấm nền AMOLED của Samsung Galaxy S7:
```bash
# 1. Luôn giữ màn hình thức khi có sạc (USB/AC/Wireless):
adb -s <serial> shell settings put global stay_on_while_plugged_in 7
adb -s <serial> shell svc power stayon true
adb -s <serial> shell settings put system screen_off_timeout 2147483647

# 2. Hạ độ sáng về mức 0 (tiết kiệm điện, OLED không sinh nhiệt, không ám màn):
adb -s <serial> shell settings put system screen_brightness 0
```

---

## 4. Kỷ luật vận hành Watchdog Tự Động (`farm_adb_transport_auto_healer.py`)
Khi triển khai watchdog tự động phục hồi kẹt socket ADB theo chu kỳ (3-5 phút):
1. **Kiểm tra khóa thiết bị (Bulkhead Lock Guard):** BẮT BUỘC đọc `~/.codex/device-locks/*.lock.json`. Nếu máy đang có tiến trình tự động hóa hoạt động (PID còn sống) ➔ BỎ QUA NGAY (`status: LOCKED`), tuyệt đối không gửi `reconnect` hay `keyevent` làm ngắt quãng tác vụ đang chạy.
2. **Ping timeout cực ngắn (2.5s):** Quét song song với timeout <= 2.5s. Chỉ kích hoạt `reconnect` khi gặp `TimeoutExpired` hoặc thiết bị ở trạng thái `offline`.
3. **Telemetry & Silent Watchdog:** Ghi nhận structured JSON metric ra `sys.stderr` với nhãn `[TELEMETRY_METRIC]`. Tuyệt đối giữ `stdout` rỗng khi farm ở trạng thái khỏe mạnh để không gây nhiễu log / spam kênh thông báo.
