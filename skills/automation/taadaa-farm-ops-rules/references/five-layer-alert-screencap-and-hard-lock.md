# Quy chuẩn Khóa Cứng (Hard Lock 2h) & Chụp Ảnh Alert Đa Tầng (5-Layer Fallback)

## 1. Quy chuẩn Khóa Cứng Thiết Bị Khi Lỗi (Hard Lock 2h)
- **Mục đích:** Khi máy gặp lỗi (sai UI, popup lạ, crash, kẹt navigation, timeout...), BẮT BUỘC giữ nguyên hiện trường màn hình để người vận hành hoặc Hermes Agent điều tra phân tích.
- **Vị trí Lock:** Lưu file `machine_<N>.lock.json` tại `~/.codex/device-locks/`.
- **Cấu hình bắt buộc:**
  ```json
  {
    "machine": <N>,
    "serial": "<SERIAL>",
    "status": "blocked",
    "reason": "<ERROR_REASON>",
    "ttl_seconds": 7200,
    "lock_type": "hard_incident_hold"
  }
  ```
- **Thời hạn giải phóng (TTL):** Đúng **2 tiếng (7200s)**.
  - Trong vòng 2 tiếng: Tuyệt đối CẤM các tiến trình dọn dẹp (`reap-dead-owner-locks`), cron schedule hay runner khác tự ý xóa lock hoặc tương tác lên máy làm mất hiện trường.
  - Sau 2 tiếng: Nếu người dùng không can thiệp, hệ thống mới được phép nhả lock để giải phóng máy vào các ca tiếp theo.

---

## 2. Kiến trúc Chụp Ảnh Cảnh Báo Đa Tầng (5-Layer Fallback Alert Screencap)
Khi phát sinh Farm Alert gửi Telegram (`send_farm_machine_alert`), bộ phát alert BẮT BUỘC tuân thủ 5 tầng fallback để đảm bảo luôn gửi kèm ảnh hiện trường có gắn Banner Đỏ:

1. **Layer 1 (Primary Screencap):**
   - Chạy `adb exec-out screencap -p` với timeout 10s.
   - Nếu trả về > 1000 bytes: Sử dụng ngay.

2. **Layer 2 (ATX-Agent / UiAutomator2 JSON-RPC):**
   - Mở port forward cục bộ `tcp:0` trỏ tới `tcp:7912` (hoặc `tcp:9008`).
   - Gửi yêu cầu `takeScreenshot` qua JSON-RPC.
   - **Pitfall & Tự Phục Hồi:** Nếu uiautomator backend trên máy chưa chạy hoặc trả về `502 Bad Gateway`, gửi ngay lệnh `POST /uiautomator` với `{}` để đánh thức tiến trình uiautomator stub, đợi 0.5s rồi gọi lại `takeScreenshot`. Tầng này bypass triệt để lỗi SurfaceFlinger bị chặn framebuffer (`FB is protected: PERMISSION_DENIED`).

3. **Layer 3 (ADB Transport Reconnect):**
   - Nếu kết nối ADB bị treo/timeout (máy vẫn hiện `device` nhưng không phản hồi shell), gọi lệnh `adb -s <serial> reconnect` để khởi động lại tầng transport riêng của thiết bị, đợi 1.5s rồi thử lại Layer 2 (ATX).

4. **Layer 4 (Shell SDCard Buffer):**
   - Chạy `adb shell screencap /sdcard/__alert_screencap.png` -> đọc ra qua `adb exec-out cat` -> dọn sạch file tạm.

5. **Layer 5 (Artifact Session Fallback):**
   - Nếu toàn bộ các lệnh ADB live thất bại, quét tìm file ảnh `screen.png` mới nhất được sinh ra trong thư mục artifact của máy (`D:\Taadaa\runtime\kibe\live\.../machine_<N>/.../screen.png`) trong vòng 4–24h gần nhất.
   - Gắn Banner Đỏ lên ảnh artifact đó và gửi về nhóm Telegram.
