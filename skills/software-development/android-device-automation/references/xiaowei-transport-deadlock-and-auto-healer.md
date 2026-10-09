# Xử lý dứt điểm kẹt socket ADB Transport Deadlock và lỗi ngắt kết nối Xiaowei (放卫)

## 1. Bản chất sự cố kép (Kẹt Socket + Rớt Luồng Video)
- **Kẹt socket `adbd` (Deadlock tầng USB Transport):**
  - Thiết bị: Samsung Galaxy S7 (Android 8.0).
  - Nguyên nhân: Kênh USB vật lý bị quá tải buffer khi đồng thời phục vụ luồng stream liên tục của Xiaowei qua `XWCaptureScreen.jar` và các đợt ping/quét shell từ nhiều tiến trình cron/watchdog.
  - Hậu quả: `adbd` trên điện thoại rơi vào trạng thái khóa futex (`futex_wait_queue_me`), khiến socket rơi vào half-closed. ADB Server trên máy tính vẫn hiển thị thiết bị là `device` (không hề báo offline), nhưng toàn bộ lệnh `adb shell` gửi tới đều bị nghẽn (hang/timeout >10s).
- **Lỗi hình ảnh Xiaowei (Màn hình cam "Phone disconnected"):**
  - Nguyên nhân: Khi máy rảnh và tắt màn hình (Doze / Sleep mode), GPU của Android ngắt buffer vẽ màn hình. Tốc độ khung hình về 0 FPS khiến Xiaowei nhận định mất tín hiệu video và hiện icon cam ngắt kết nối.
- **Lỗi phần cứng vật lý:**
  - Thiết bị mất hẳn khỏi `adb devices`. Kiểm tra PowerShell `Get-PnpDevice` trả về `CM_PROB_PHANTOM` (`Present: False`) ➔ Cáp lỏng/tuột hub hoặc máy hỏng/sập nguồn. Người dùng chỉ thị loại bỏ máy hỏng ra khỏi fleet theo dõi.

---

## 2. Kỹ thuật cứu hộ O(1) không cần chạm tay vào máy
1. **Giải phóng socket kẹt tức thì bằng `reconnect`:**
   ```bash
   adb -s <serial> reconnect
   # Đối với cụm Admin Remote:
   adb -H 192.168.110.119 -P 5037 -s <serial> reconnect
   ```
   Lệnh này ép ADB server reset pipe USB và thương lượng lại kết nối với `adbd` trong < 1.5 giây. Thiết bị thoát khỏi kẹt socket ngay lập tức.
2. **Đánh thức màn hình để phục hồi stream Xiaowei:**
   ```bash
   adb -s <serial> shell input keyevent 224
   ```
   Lệnh đánh thức kích hoạt lại Surface GPU rendering, giúp Xiaowei bắt lại luồng video tự động.

---

## 3. Kiến trúc Watchdog tự động hoá dứt điểm (`farm_adb_transport_auto_healer.py`)
Triển khai watchdog tự hành mỗi 3 phút (`*/3 * * * *`, `no_agent=True`):
- **Cơ chế Bulkhead Lock Guard:** Đọc danh sách khóa `~/.codex/device-locks/*.lock.json`. Nếu thiết bị đang có task tự động hóa hoạt động (PID alive) ➔ **bỏ qua ngay lập tức** để không gây đứt gãy phiên chạy ngầm.
- **Kiểm tra song song & Timeout ngắn:** Quét đồng thời toàn bộ dàn máy qua `ThreadPoolExecutor` với timeout ping = 2.5s.
- **Can thiệp đúng đối tượng:** Chỉ gửi `reconnect` và wake-up khi thiết bị rơi vào `HUNG` hoặc `offline`.
- **Silent Watchdog Pattern:** Ghi nhận structured JSON metric ra `sys.stderr` với nhãn `[TELEMETRY_METRIC]`, giữ `stdout` rỗng khi trạng thái bình thường để chống spam chat.
