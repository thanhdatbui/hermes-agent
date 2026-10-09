# 5-Layer Alert Screencap Fallback & 2h Hard Lock Architecture

## 1. Hard Incident Lock (TTL: 2 Hours / 7200s)
Khi phát hiện thiết bị bị lỗi (màn hình lạ, popup ngoài dự kiến, lỗi navigation profile, upload/feed fail):
- **Cơ chế:** Tạo lock file cứng `~/.codex/device-locks/machine_<N>.lock.json` với `status: "blocked"`, `ttl_seconds: 7200`.
- **Mục đích:** Giữ nguyên trạng thái hiển thị trên màn hình máy để người vận hành kiểm tra, ngăn các worker khác hoặc cron tick tiếp theo đè lên làm mất hiện trường.
- **Giải phóng:** Không được tự ý xóa lock trong 2 giờ đầu. Sau 2 giờ không có can thiệp từ người dùng, cơ chế reap lock mới được phép nhả lock.

## 2. Farm Alert Screencap Multi-Layer Architecture
Khi gửi Farm Alert (`send_farm_machine_alert`), bộ phát áp dụng 5 tầng fallback để đảm bảo luôn trích xuất được ảnh:
1. **Layer 1 (Primary Screencap):** `adb exec-out screencap -p` (10s timeout).
2. **Layer 2 (ATX-Agent / UiAutomator2 JSON-RPC):** Port-forward tới 7912 / 9008 -> gọi `takeScreenshot` (bypass SurfaceFlinger `FB is protected: PERMISSION_DENIED`). Nếu uiautomator backend chưa chạy (502 Bad Gateway), gửi `POST /uiautomator` để khởi động lại stub trước khi chụp.
3. **Layer 3 (ADB Reconnect):** Nếu ADB transport bị treo (timeout khi gửi lệnh shell), gọi `adb -s <serial> reconnect` để thiết lập lại kết nối cục bộ mà không ảnh hưởng tới các máy khác, sau đó thử lại Layer 2 qua ATX.
4. **Layer 4 (Shell SDCard Buffer):** Chụp qua file đệm `/sdcard/__alert_screencap.png` rồi đọc ra bằng `adb exec-out cat`.
5. **Layer 5 (Artifact Session Search):** Quét thư mục runtime/artifact (`D:/Taadaa/runtime/kibe/live/.../machine_<N>/.../screen.png`) tìm file ảnh chụp gần nhất của phiên để gắn Banner Đỏ.
